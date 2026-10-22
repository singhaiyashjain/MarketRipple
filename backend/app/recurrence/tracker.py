"""Recurring-news tracker (time series over analysed events). OWNER: M4
Every analysed event is logged to MongoDB (collection `events_log`; same MONGODB_URI as saved analyses). For each
graph node ("star") we then look at a rolling window and ask: how many DISTINCT stories hit this star, how many with a
negative effect, how recent, and is it speeding up?  A star with enough negative stories is an ALERT (the UI opens it
and makes it blink); fewer is a WATCH. Replay / sample (simulated) events are stored with a flag and can be excluded.

If MONGODB_URI is not set the log lives in memory (lost on restart) so the feature still works for a demo.

Honest limits: a "story" is one analysed event, de-duplicated against near-identical headlines from the last
24 h (live news only). The effect label is the graph's, not a price forecast.
"""
from __future__ import annotations

import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.graph import store
from app.quant import data_loader
from app.quant.backtest import MARKET_NODE, backtest_pair, entry_node, event_sign

_WORD = re.compile(r"[a-z0-9]{4,}")
KEEP_DAYS = 120
COLLECTION = "events_log"


# ------------------------------------------------------------------ storage (MongoDB, or memory when Mongo is off)
class _Mongo:
    """events_log in MongoDB. `ts` is a UTC ISO string, so string comparison is time comparison."""
    def __init__(self) -> None:
        self.col = store._collection(COLLECTION)
        try:
            self.col.create_index("ts")
        except Exception:
            pass                                                   # index is an optimisation only

    def insert(self, doc: dict) -> None:
        self.col.insert_one(dict(doc))

    def headlines(self, since: str) -> list[str]:
        return [d["headline"] for d in self.col.find({"simulated": False, "ts": {"$gte": since}}, {"headline": 1})]

    def rows(self, since: str, include_simulated: bool) -> list[dict]:
        q: dict = {"ts": {"$gte": since}}
        if not include_simulated:
            q["simulated"] = False
        out = []
        for d in self.col.find(q).sort("ts", 1):
            d.pop("_id", None)
            out.append(d)
        return out

    def prune(self, before: str) -> None:
        self.col.delete_many({"ts": {"$lt": before}})

    def clear(self, simulated_only: bool) -> int:
        return self.col.delete_many({"simulated": True} if simulated_only else {}).deleted_count


class _Memory:
    def __init__(self) -> None:
        self.docs: list[dict] = []
        self.lock = threading.Lock()

    def insert(self, doc: dict) -> None:
        with self.lock:
            self.docs.append(dict(doc))

    def headlines(self, since: str) -> list[str]:
        return [d["headline"] for d in self.docs if not d["simulated"] and d["ts"] >= since]

    def rows(self, since: str, include_simulated: bool) -> list[dict]:
        return sorted((dict(d) for d in self.docs if d["ts"] >= since and (include_simulated or not d["simulated"])), key=lambda d: d["ts"])

    def prune(self, before: str) -> None:
        with self.lock:
            self.docs = [d for d in self.docs if d["ts"] >= before]

    def clear(self, simulated_only: bool) -> int:
        with self.lock:
            keep = [d for d in self.docs if simulated_only and not d["simulated"]]
            n = len(self.docs) - len(keep)
            self.docs = keep
            return n


_memory = _Memory()
_mongo: _Mongo | None = None


def _log():
    """The active log. Mongo errors propagate (callers log them); a DB in back-off raises RuntimeError."""
    global _mongo
    if not settings.mongodb_uri:
        return _memory
    store.guard()
    try:
        if _mongo is None or _mongo.col is not store._collection(COLLECTION):
            _mongo = _Mongo()
        return _mongo
    except Exception:
        store.failed()
        raise


def storage_kind() -> str:
    return "mongodb" if settings.mongodb_uri else "memory"


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tokens(t: str) -> set[str]:
    return set(_WORD.findall((t or "").lower()))


def _similar(a: set[str], b: set[str]) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= 0.5


def _parse(ts: str) -> datetime:
    d = datetime.fromisoformat(ts)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ write
def record_event(resp: dict, headline: str, ts: datetime | None = None, simulated: bool = False,
                 region: str | None = None, kind: str = "live") -> bool:
    """Log one analysed event. Returns False when skipped (canned sample, no graph, or a duplicate story)."""
    if resp.get("mode") == "mock" or not resp.get("nodes"):
        return False                                           # canned sample = nothing real to count
    ts = ts or _now()
    nodes = [{"id": n["id"], "label": n["label"], "effect": n.get("effect", "unknown"), "type": n.get("type")}
             for n in resp["nodes"] if n.get("type") != "event"]
    if not nodes:
        return False
    ev = resp.get("event") or {}
    simulated = bool(simulated or ev.get("is_simulated"))
    log = _log()
    try:
        if not simulated:                                      # same story seen again within 24 h is not a new story
            tk = _tokens(headline)
            if any(_similar(tk, _tokens(h)) for h in log.headlines(_iso(ts - timedelta(hours=24)))):
                return False
        log.insert({"ts": _iso(ts), "headline": headline[:300], "entry_node": entry_node(resp), "shock_sign": event_sign(resp),
                    "direction": ev.get("direction"), "change_pct": ev.get("change_pct"), "region": region, "kind": kind,
                    "simulated": simulated, "nodes": nodes})
        log.prune(_iso(ts - timedelta(days=KEEP_DAYS)))
    except RuntimeError:
        raise
    except Exception:
        if settings.mongodb_uri:
            store.failed()
        raise
    return True


def clear(simulated_only: bool = False) -> int:
    return _log().clear(simulated_only)


# ------------------------------------------------------------------ read
def _rows(window_days: float, include_simulated: bool, now: datetime) -> list[dict]:
    out = []
    for d in _log().rows(_iso(now - timedelta(days=window_days)), include_simulated):
        d["dt"] = _parse(d["ts"])
        out.append(d)
    return out


def _level(neg: int, direct: int) -> str:
    if neg >= settings.recur_alert_hits:
        return "alert"
    if neg >= settings.recur_watch_hits or direct >= settings.recur_alert_hits:
        return "watch"
    return "none"


def _reason(sig: dict, window_days: float) -> str:
    d = f"{window_days:g}-day"
    if sig["level"] == "alert":
        return f"{sig['negative']} separate stories with a negative effect on this star in the last {d} window."
    if sig["negative"] >= settings.recur_watch_hits:
        return f"{sig['negative']} negative stories in the last {d} window; one more makes it an alert."
    return f"{sig['direct']} stories directly about this star in the last {d} window."


def compute_signals(window_days: float | None = None, include_simulated: bool = True, now: datetime | None = None) -> dict:
    """Per-node recurrence signals over the rolling window."""
    window_days = float(window_days or settings.recur_window_days)
    now = now or _now()
    rows = _rows(window_days, include_simulated, now)
    half = max(settings.recur_half_life_days, 0.1)
    mid = now - timedelta(days=window_days / 2)
    acc: dict[str, dict] = {}
    for ev in rows:
        age_days = max(0.0, (now - ev["dt"]).total_seconds() / 86400)
        decay = 0.5 ** (age_days / half)
        for n in ev["nodes"]:
            a = acc.setdefault(n["id"], {"node_id": n["id"], "label": n["label"], "hits": 0, "negative": 0, "positive": 0,
                                         "mixed": 0, "direct": 0, "simulated_hits": 0, "score": 0.0, "recent_neg": 0,
                                         "earlier_neg": 0, "last_ts": None, "stories": [], "drivers": defaultdict(int)})
            a["label"] = n["label"]
            a["hits"] += 1
            eff = n.get("effect")
            if eff in ("negative", "positive", "mixed"):
                a[eff] += 1
            if ev["entry_node"] == n["id"]:
                a["direct"] += 1
            if ev["simulated"]:
                a["simulated_hits"] += 1
            if eff == "negative":
                a["score"] += decay
                a["recent_neg" if ev["dt"] >= mid else "earlier_neg"] += 1
                if ev["entry_node"] and ev["shock_sign"] in (-1, 1):
                    a["drivers"][(ev["entry_node"], ev["shock_sign"])] += 1
            a["last_ts"] = ev["ts"]
            a["stories"].append({"ts": ev["ts"], "headline": ev["headline"], "effect": eff, "simulated": bool(ev["simulated"]),
                                 "entry_node": ev["entry_node"], "direction": ev["direction"], "region": ev["region"]})
    nodes = {}
    for nid, a in acc.items():
        trend = "rising" if a["recent_neg"] > a["earlier_neg"] else "easing" if a["recent_neg"] < a["earlier_neg"] else "steady"
        sig = {
            "node_id": nid, "label": a["label"], "window_days": window_days, "hits": a["hits"], "negative": a["negative"],
            "positive": a["positive"], "mixed": a["mixed"], "direct": a["direct"], "simulated_hits": a["simulated_hits"],
            "score": round(a["score"], 3), "trend": trend if a["negative"] else None, "last_ts": a["last_ts"],
            "level": _level(a["negative"], a["direct"]),
            "stories": list(reversed(a["stories"]))[:8],
            "drivers": [{"node": k[0], "shock_sign": k[1], "count": c}
                        for k, c in sorted(a["drivers"].items(), key=lambda kv: -kv[1])],
        }
        sig["reason"] = _reason(sig, window_days) if sig["level"] != "none" else ""
        nodes[nid] = sig
    ranked = sorted(nodes.values(), key=lambda s: (-s["score"], s["node_id"]))
    return {
        "window_days": window_days, "include_simulated": include_simulated, "generated_at": now.isoformat(),
        "thresholds": {"alert_hits": settings.recur_alert_hits, "watch_hits": settings.recur_watch_hits,
                       "half_life_days": half},
        "events_in_window": len(rows),
        "alerts": [s["node_id"] for s in ranked if s["level"] == "alert"],
        "watch": [s["node_id"] for s in ranked if s["level"] == "watch"],
        "nodes": nodes,
        "_rows": rows,
    }


def public_signals(**kw) -> dict:
    out = compute_signals(**kw)
    out.pop("_rows", None)
    return out


# ------------------------------------------------------------------ "last 5 times this happened" for a blinking star
def star_backtest(node_id: str, window_days: float | None = None, include_simulated: bool = True) -> dict:
    """What happened historically after the shock that keeps recurring for this star."""
    sig_all = compute_signals(window_days, include_simulated)
    rows = sig_all.pop("_rows")
    sig = sig_all["nodes"].get(node_id)
    if not sig or not sig["drivers"]:
        return {"available": False, "node_id": node_id, "caveat": "",
                "reason": "No recurring news with a known driver has hit this star in the window, so there is no event to look up."}
    top = sig["drivers"][0]
    sibs: dict[str, dict] = defaultdict(lambda: {"label": "", "count": 0})
    for ev in rows:
        if ev["entry_node"] == top["node"] and ev["shock_sign"] == top["shock_sign"]:
            if any(n["id"] == node_id and n.get("effect") == "negative" for n in ev["nodes"]):
                for n in ev["nodes"]:
                    if n["id"] != node_id and n.get("effect") == "negative" and data_loader.ticker_for(n["id"]):
                        sibs[n["id"]]["label"] = n["label"]
                        sibs[n["id"]]["count"] += 1
    targets = [{"id": node_id, "label": sig["label"], "effect": "negative"}]
    targets += [{"id": k, "label": v["label"], "effect": "negative"}
                for k, v in sorted(sibs.items(), key=lambda kv: -kv[1]["count"])[:3]]
    if top["node"] == MARKET_NODE:
        targets = [t for t in targets if t["id"] != MARKET_NODE]
    labels = {n["id"]: n["label"] for ev in rows for n in ev["nodes"]}
    out = backtest_pair(top["node"], top["shock_sign"], targets, driver_label=labels.get(top["node"], top["node"]))
    out["node_id"] = node_id
    out["other_drivers"] = sig["drivers"][1:4]
    return out
