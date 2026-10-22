"""Historical backtest: "the last 5 times this happened, here is what moved". OWNER: M4
Uses ONLY the cached daily closes in data/cache/ (no network). Everything returned comes from those CSVs;
nothing is estimated for a date that has no data. Builds on quant.event_study.

Pipeline: driver series -> past same-direction shocks (|z| >= shock_sigma vs prior 60-day vol, shocks < 5
trading days apart merged) -> for each affected asset: return and market-adjusted abnormal return (CAR)
from the shock day through +1/+5/+20 trading days -> hit-rate and "does history agree with the graph?".
"""
from __future__ import annotations

import pandas as pd

from app.quant import data_loader
from app.quant.event_study import run_event_study

WINDOWS = (1, 5, 20)
PRIMARY = 5                    # window used for hit-rate headline and the agree / disagree verdict
MIN_EPISODES = 3               # below this: "insufficient history", no averages
MERGE_GAP = 5                  # trading days; closer shocks are one episode
SHOW_LAST = 5
MAX_TARGETS = 8
MARKET_NODE = "nifty"
CAVEAT = "Historical co-movement of proxy tickers, small sample, not a prediction or proof of causation."
METHOD = ("A past shock = a day when the driver moved at least {sig:g} standard deviations {way} versus its previous "
          "60 trading days (shocks within {gap} days are merged). For each asset we show the return from the shock day "
          "through +1/+5/+20 trading days and the abnormal return, i.e. what is left after removing what the Nifty 50 "
          "explains (market model fitted on the ~100 days before the shock). Shocks in the last 20 trading days are "
          "left out because their outcome is not complete yet.")


def _unavailable(reason: str, **extra) -> dict:
    return {"available": False, "reason": reason, "caveat": CAVEAT, **extra}


def _sign(x: float | None) -> int:
    return 0 if x is None or x == 0 else (1 if x > 0 else -1)


def predicted_sign(effect: str | None) -> int | None:
    """Graph effect -> expected direction of the asset's price: positive => up, negative => down, else unknown."""
    return {"positive": 1, "negative": -1}.get(effect or "")


def _episode_row(ep: dict, use_abnormal: bool) -> dict:
    ret = {str(w): {"return_pct": round(ep["raw"][w] * 100, 2),
                    "abnormal_pct": round(ep["car"][w] * 100, 2) if use_abnormal else None} for w in WINDOWS}
    return {"date": ep["date"], "driver_move_pct": ep["driver_move_pct"], "returns": ret}


def _verdict(mean5: float | None, hit5: float | None, pred: int | None, n: int, t5: float | None) -> tuple[bool | None, str | None]:
    """(agrees, leans). agrees: True/False only when the +5d result is statistically distinguishable from noise
    (|t| >= 2); with no t-stat (raw-only series) a hit-rate of >=0.7 / <=0.3 is required instead.
    leans: 'with' / 'against' / None = direction of the average + hit-rate even when it is NOT significant."""
    if pred is None or n < MIN_EPISODES or mean5 is None or hit5 is None:
        return None, None
    leans = "with" if _sign(mean5) == pred and hit5 >= 0.5 else "against" if _sign(mean5) == -pred and hit5 < 0.5 else None
    solid = abs(t5) >= 2 if t5 is not None else (hit5 >= 0.7 or hit5 <= 0.3)
    if leans == "with" and solid:
        return True, leans
    if leans == "against" and solid:
        return False, leans
    return None, leans


def _one_target(driver: pd.Series, market: pd.Series, node: dict, ticker: str, shock_sign: int,
                shock_sigma: float, use_abnormal: bool) -> tuple[dict, list[float]]:
    asset = data_loader.load_prices(ticker)
    px = pd.concat([driver, asset, market], axis=1, join="inner").dropna()   # one common trading calendar
    if len(px) < 300:
        raise ValueError(f"only {len(px)} overlapping days")
    res = run_event_study(px.iloc[:, 0], px.iloc[:, 1], px.iloc[:, 2], shock_sigma=shock_sigma,
                          windows=WINDOWS, shock_sign=shock_sign, min_gap=MERGE_GAP)
    eps = res["episodes"]
    n = res["n"]
    pred = predicted_sign(node.get("effect"))
    out = {"node_id": node["id"], "label": node.get("label", node["id"]), "ticker": ticker,
           "predicted": {1: "up", -1: "down", None: "unclear"}[pred], "graph_effect": node.get("effect"),
           "adjusted_for_market": use_abnormal, "n": n,
           "last_episodes": [_episode_row(e, use_abnormal) for e in reversed(eps[-SHOW_LAST:])],
           "date_range": {"start": str(px.index[0].date()), "end": str(px.index[-1].date())},
           "stats": None, "hit_rate": None, "agrees": None, "leans": None, "significant": None}
    if n < MIN_EPISODES:
        out["note"] = f"Insufficient history: only {n} comparable past shock(s) found (need {MIN_EPISODES})."
        return out, [e["driver_move_pct"] for e in eps]

    key = "car" if use_abnormal else "raw"
    mean_ret, mean_abn, tstat, hit = {}, {}, {}, {}
    for w in WINDOWS:
        raws = [e["raw"][w] for e in eps]
        vals = [e[key][w] for e in eps]
        mean_ret[str(w)] = round(sum(raws) / n * 100, 2)
        if use_abnormal:
            mean_abn[str(w)] = round(sum(e["car"][w] for e in eps) / n * 100, 2)
        if use_abnormal and w in res["t_stat"]:
            tstat[str(w)] = res["t_stat"][w]
        hit[str(w)] = round(sum(1 for v in vals if pred is not None and _sign(v) == pred) / n, 2) if pred else None
    out["stats"] = {"mean_return_pct": mean_ret, "mean_abnormal_pct": mean_abn or None, "t_stat": tstat or None}
    out["hit_rate"] = hit if pred else None
    base = mean_abn if use_abnormal else mean_ret
    t5 = tstat.get(str(PRIMARY))
    out["agrees"], out["leans"] = _verdict(base.get(str(PRIMARY)), hit[str(PRIMARY)] if pred else None, pred, n, t5)
    out["significant"] = None if t5 is None else abs(t5) >= 2
    return out, [e["driver_move_pct"] for e in eps]


def _summary(driver_label: str, up: bool, t: dict) -> str:
    if t["n"] < MIN_EPISODES:
        return f"{t['label']}: insufficient history ({t['n']} past shock{'s' if t['n'] != 1 else ''})."
    h = (t["hit_rate"] or {}).get(str(PRIMARY))
    m = ((t["stats"] or {}).get("mean_abnormal_pct") or (t["stats"] or {}).get("mean_return_pct") or {}).get(str(PRIMARY))
    way = "rose" if up else "fell"
    part = f"{t['label']}: in {t['n']} past episodes where {driver_label} {way} sharply, "
    if h is None:
        return part + f"it moved on average {m:+.2f}% over the next 5 trading days (graph effect unclear, no hit-rate)."
    return part + (f"it moved the way the graph predicts ({t['predicted']}) in {round(h * t['n'])} "
                   f"of {t['n']} at +5 days; average {m:+.2f}%.")


def backtest_pair(driver_node: str, shock_sign: int, targets: list[dict], change_pct: float | None = None,
                  shock_sigma: float = 2.0, driver_label: str | None = None) -> dict:
    """Backtest one driver shock against several graph nodes.
    targets: [{id, label, effect}], effect = the graph's predicted effect on that node (positive/negative/...)."""
    if shock_sign not in (-1, 1):
        return _unavailable("The event direction is unknown, so there is no past shock of the same direction to look up.")
    d_ticker = data_loader.ticker_for(driver_node)
    if not d_ticker:
        return _unavailable(f"'{driver_node}' has no price proxy in data/tickers.json, so there is no price history to test against.")
    m_ticker = data_loader.ticker_for(MARKET_NODE)
    try:
        driver = data_loader.load_prices(d_ticker)
        market = data_loader.load_prices(m_ticker)
    except FileNotFoundError as exc:
        return _unavailable(f"{exc}")

    results, skipped, seen = [], [], {d_ticker}
    use_abn_base = d_ticker != m_ticker
    moves: list[float] = []
    for node in targets:
        if len(results) >= MAX_TARGETS:
            break
        t = data_loader.ticker_for(node["id"])
        if not t:
            skipped.append({"node_id": node["id"], "reason": "no price proxy ticker"})
            continue
        if t in seen:
            skipped.append({"node_id": node["id"], "reason": f"same series as {'the driver' if t == d_ticker else 'another target'} ({t})"})
            continue
        try:
            row, mv = _one_target(driver, market, node, t, shock_sign, shock_sigma,
                                  use_abnormal=use_abn_base and t != m_ticker)
        except FileNotFoundError:
            skipped.append({"node_id": node["id"], "reason": f"no cached prices for {t}"})
            continue
        except ValueError as exc:
            skipped.append({"node_id": node["id"], "reason": str(exc)})
            continue
        seen.add(t)
        results.append(row)
        if len(mv) > len(moves):
            moves = mv
    if not results:
        return _unavailable("None of the affected nodes has usable cached price history.", skipped=skipped)

    up = shock_sign > 0
    dl = driver_label or d_ticker
    way = "up" if up else "down"
    out = {
        "available": True,
        "driver": {"node": driver_node, "label": driver_label or driver_node, "ticker": d_ticker,
                   "direction": way, "shock_sigma": shock_sigma},
        "market": {"node": MARKET_NODE, "ticker": m_ticker},
        "windows": list(WINDOWS), "primary_window": PRIMARY,
        "targets": results, "skipped": skipped,
        "date_range": {"start": min(r["date_range"]["start"] for r in results),
                       "end": max(r["date_range"]["end"] for r in results)},
        "method": METHOD.format(sig=shock_sigma, way="up" if up else "down", gap=MERGE_GAP),
        "caveat": CAVEAT,
    }
    for r in results:
        r["summary"] = _summary(dl, up, r)
    if change_pct is not None and moves:
        mags = sorted(abs(x) for x in moves)
        stated = abs(float(change_pct))
        out["size_comparison"] = {
            "stated_pct": float(change_pct), "historical_shocks": len(mags),
            "median_historical_move_pct": round(mags[len(mags) // 2], 2), "largest_historical_move_pct": round(mags[-1], 2),
            "share_of_history_smaller": round(sum(1 for m in mags if m < stated) / len(mags), 2),
            "note": "Historical figures are single-day driver moves; the stated move in the news may cover a different period.",
        }
    return out


def entry_node(resp: dict) -> str | None:
    link = (resp.get("meta") or {}).get("entity_link") or {}
    if link.get("node"):
        return link["node"]
    ev = next((n["id"] for n in resp.get("nodes", []) if n.get("type") == "event"), None)
    e = next((e for e in resp.get("edges", []) if e.get("source") == ev), None)
    return e["target"] if e else None


def event_sign(resp: dict) -> int:
    edge = next((e for e in resp.get("edges", []) if e.get("id") == "e_event"), None)
    if edge and edge.get("sign") in (-1, 1):
        return int(edge["sign"])
    return {"increase": 1, "decrease": -1}.get((resp.get("event") or {}).get("direction") or "", 0)


def pick_targets(resp: dict, entry: str | None) -> list[dict]:
    """Affected nodes from the strongest paths: path end-points first, then intermediate nodes."""
    nodes = {n["id"]: n for n in resp.get("nodes", [])}
    paths = sorted(resp.get("paths", []), key=lambda p: -p.get("strength", 0))
    order: list[str] = []
    for ids in ([p["node_ids"][-1:] for p in paths] + [p["node_ids"][1:-1] for p in paths]):
        for nid in ids:
            if nid not in order and nid != entry and nodes.get(nid, {}).get("type") != "event":
                order.append(nid)
    return [{"id": i, "label": nodes[i]["label"], "effect": nodes[i].get("effect")} for i in order if i in nodes]


def backtest_analysis(resp: dict, shock_sigma: float = 2.0) -> dict:
    """Backtest for a full /api/analyze response (dict)."""
    entry = entry_node(resp)
    if not entry:
        return _unavailable("This event is not linked to a node of the impact graph.")
    label = next((n["label"] for n in resp.get("nodes", []) if n["id"] == entry), entry)
    out = backtest_pair(entry, event_sign(resp), pick_targets(resp, entry),
                        change_pct=(resp.get("event") or {}).get("change_pct"),
                        shock_sigma=shock_sigma, driver_label=label)
    out["simulated_event"] = bool((resp.get("event") or {}).get("is_simulated"))
    return out
