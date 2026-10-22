"""Background monitor: poll feeds -> detect new market-moving news -> run the analysis pipeline -> keep history.

Plain threads (no asyncio) so the sync pipeline can be called directly. State is in memory.
Replay mode feeds saved, simulated sample events through the SAME pipeline (demo-safe).
"""
from __future__ import annotations

import json
import logging
import re
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.config import DATA_DIR, settings
from app.live import feeds as feedlib
from app.live import newsapi

log = logging.getLogger("finpulse.live")

GLOBAL_SAMPLES = {"fed_hike", "oil_shock"}          # replay samples tagged Global; the rest are India
_WORD = re.compile(r"[a-z0-9]{4,}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def _tokens(t: str) -> set[str]:
    return set(_WORD.findall(t.lower()))


def _similar(a: set[str], b: set[str]) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= 0.5


def _norm_region(region: str | None) -> str:
    r = (region or "all").lower()
    return r if r in feedlib.REGIONS else "all"


class Monitor:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.poll_lock = threading.Lock()
        self.wake = threading.Event()
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

        self.headlines: list[dict] = []
        self.seen: set[str] = set()
        self.events: deque[dict] = deque(maxlen=40)          # newest first
        self.event_by_title: dict[str, int] = {}             # headline (lower) -> event version
        self.version = 0
        self.replay = False
        self.replay_idx = 0
        self.feed_status: dict[str, dict] = {}
        self.api_state = "ok"
        self.last_poll_at: datetime | None = None
        self.next_poll_at: datetime | None = None
        self.last_poll_ok: bool | None = None
        self.last_error: str | None = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self._loop, name="finpulse-live", daemon=True)
        self.thread.start()

    def shutdown(self) -> None:
        self.stop.set()
        self.wake.set()

    def _loop(self) -> None:
        first = True
        while not self.stop.is_set():
            try:
                if self.replay and not first:
                    self.fire_next()
                    wait = settings.replay_interval_seconds
                else:
                    self.poll()
                    wait = settings.live_poll_seconds
                first = False
            except Exception:                                  # never let the loop die
                log.exception("live loop error")
                wait = 30
            with self.lock:
                self.next_poll_at = _now() + timedelta(seconds=wait)
            self.wake.wait(wait)
            self.wake.clear()

    # ------------------------------------------------------------------ polling
    def _collect(self) -> list[dict]:
        items: list[dict] = []
        ok_any = False

        def one(f):
            name, url, region = f
            try:
                rows = feedlib.fetch_feed(name, url, region)
                return name, region, rows, None
            except Exception as exc:                          # network / XML errors: mark feed as down
                return name, region, [], f"{type(exc).__name__}"

        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(one, feedlib.FEEDS))
        status = {}
        for name, region, rows, err in results:
            status[name] = {"ok": err is None, "region": region, "count": len(rows), **({"error": err} if err else {})}
            ok_any = ok_any or err is None
            items.extend(rows)
        with self.lock:
            self.feed_status = status

        if settings.news_api_provider == "newsapi" and settings.news_api_key:
            try:
                items.extend(newsapi.fetch(settings.news_api_key))
                self.api_state = "ok"
            except Exception as exc:
                self.api_state = f"error: {exc}"[:80]
        self._ok_any = ok_any
        return items

    def poll(self) -> dict:
        """One check of every feed. Safe to call from the API (serialised by a lock)."""
        with self.poll_lock:
            items = self._collect()
            seen_titles = {}
            for it in items:                                   # de-dupe across outlets by exact title
                seen_titles.setdefault(it["title"].lower(), it)
            items = sorted(seen_titles.values(), key=lambda x: x["published"], reverse=True)
            # ONLY financial / project-related news is kept; everything else is dropped here, so it never
            # reaches the news panel, the ticker or the event detector.
            kept = []
            for it in items:
                c = feedlib.classify(it["title"], it["summary"])
                if c["financial"]:
                    kept.append({**it, "project": c["project"]})
            items = kept

            with self.lock:
                self.headlines = items[:150] if items else self.headlines
                self.last_poll_at = _now()
                self.last_poll_ok = bool(items) or getattr(self, "_ok_any", False)
                self.last_error = None if self.last_poll_ok else "No feed responded"

            fresh = [i for i in items if i["title"].lower() not in self.seen]
            self.seen.update(i["title"].lower() for i in items)
            made = 0
            made_by = {"india": 0, "global": 0}              # quota is PER REGION so neither starves the other
            tries = {"india": 0, "global": 0}
            used: list[set[str]] = []
            for it in fresh:
                reg = it["region"] if it["region"] in made_by else "global"
                if made_by[reg] >= settings.live_max_events_per_poll or tries[reg] >= settings.live_max_attempts_per_region:
                    continue
                tk = _tokens(it["title"])
                if any(_similar(tk, u) for u in used):
                    continue
                cluster = [o for o in items if _similar(tk, _tokens(o["title"]))]
                sources = sorted({o["source"] for o in cluster})
                text = ". ".join(p for p in (it["title"], it["summary"]) if p)[:1500]
                tries[reg] += 1
                ev = self._add_event("live", it["title"], text, False, sources, it["region"], it.get("link"))
                if ev:
                    made += 1
                    made_by[reg] += 1
                    used.append(tk)
                    with self.lock:
                        self.event_by_title[it["title"].lower()] = ev["version"]
            return {"checked": len(items), "new_events": made}

    # ------------------------------------------------------------------ events
    def _add_event(self, kind: str, headline: str, text: str, simulated: bool,
                   sources: list[str], region: str, link: str | None = None) -> dict | None:
        from app.pipeline import run_analysis                  # lazy: keeps import light + avoids cycles
        from app.schemas import AnalyzeRequest
        try:
            resp = run_analysis(AnalyzeRequest(news=text if len(text) >= 10 else headline + " (news)", simulated=simulated))
        except Exception as exc:
            log.exception("analysis failed for live event")
            with self.lock:
                self.last_error = f"Analysis failed ({type(exc).__name__})"
            return None
        if resp.mode == "mock" and kind == "live":             # canned sample = nothing real to show for this headline
            return None
        try:                                                   # recurring-news alerts: log this event BEFORE the UI hears of it
            from app.recurrence import tracker
            tracker.record_event(resp.model_dump(mode="json"), headline, simulated=simulated, region=region, kind=kind)
        except Exception:
            log.exception("could not record event for recurrence alerts")
        with self.lock:
            self.version += 1
            ev = {"version": self.version, "kind": kind, "headline": headline, "text": text,
                  "simulated": simulated, "sources": sources, "region": region, "link": link,
                  "detected_at": _iso(_now()), "analysis": resp.model_dump(mode="json")}
            self.events.appendleft(ev)
            return ev

    def fire_next(self) -> dict | None:
        """Push the next saved sample event through the pipeline (demo)."""
        samples = json.loads((DATA_DIR / "sample_events.json").read_text(encoding="utf-8"))
        with self.lock:
            s = samples[self.replay_idx % len(samples)]
            self.replay_idx += 1
        headline = re.split(r"(?<=[.!?])\s", s["news"], maxsplit=1)[0]
        region = "global" if s["id"] in GLOBAL_SAMPLES else "india"
        return self._add_event("replay", headline, s["news"], True, [], region)

    def set_replay(self, enabled: bool) -> None:
        with self.lock:
            self.replay = bool(enabled)
        self.wake.set()

    # ------------------------------------------------------------------ reads
    def status(self) -> dict:
        with self.lock:
            top = self.events[0] if self.events else None
            key = settings.news_api_key if settings.news_api_provider == "newsapi" else ""
            return {
                "feeds": self.feed_status, "replay": self.replay,
                "api_provider": settings.news_api_provider, "api_configured": bool(key), "api": self.api_state,
                "last_poll_at": _iso(self.last_poll_at), "next_poll_at": _iso(self.next_poll_at),
                "last_poll_ok": self.last_poll_ok, "last_error": self.last_error,
                "version": self.version, "latest_region": top["region"] if top else None,
            }

    def history(self, region: str = "all", limit: int = 30) -> list[dict]:
        region = _norm_region(region)
        with self.lock:
            rows = [e for e in self.events if region == "all" or e["region"] == region]
        return [{k: v for k, v in e.items() if k not in ("analysis", "text")} for e in rows[:limit]]

    def event(self, version: int) -> dict | None:
        with self.lock:
            return next((e for e in self.events if e["version"] == version), None)

    def get_headlines(self, region: str = "all", limit: int = 60) -> dict:
        """Current news for the region. Each item says whether it looks market-moving and, when the
        graph analysis already exists for it, which event version to open."""
        region = _norm_region(region)
        with self.lock:
            live_versions = {e["version"] for e in self.events}
            rows = []
            for h in self.headlines:
                if region != "all" and h["region"] != region:
                    continue
                c = feedlib.classify(h["title"], h["summary"])
                if not c["financial"]:                       # safety net: never return non-financial news
                    continue
                ver = self.event_by_title.get(h["title"].lower())
                rows.append({**h, "relevant": True, "project": c["project"],
                             "event_version": ver if ver in live_versions else None})
                if len(rows) >= limit:
                    break
            stale = self.last_poll_at is None or (_now() - self.last_poll_at) > timedelta(seconds=settings.live_poll_seconds * 3)
            feeds = {n: {"ok": s["ok"], "region": s["region"]} for n, s in self.feed_status.items()
                     if region == "all" or s["region"] == region}
            counts = {r: sum(1 for h in self.headlines if h["region"] == r) for r in ("india", "global")}
        return {"items": rows, "feeds": feeds, "stale": stale, "region": region, "counts": counts}


monitor = Monitor()
