"""Recurring-news alerts: window, levels, de-duplication, simulated flag, API. No network, no LLM."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.recurrence import tracker

client = TestClient(app)
NOW = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)


def _resp(entry="crude", effects=None, mode="live", sign=1):
    effects = effects or {"airmargin": "negative", "banks": "mixed"}
    nodes = [{"id": "ev_x", "label": "Event", "type": "event", "effect": "neutral"},
             {"id": entry, "label": entry.title(), "type": "commodity", "effect": "positive"}]
    nodes += [{"id": k, "label": k.title(), "type": "indicator", "effect": v} for k, v in effects.items()]
    return {"mode": mode, "event": {"direction": "increase", "is_simulated": False}, "nodes": nodes,
            "edges": [{"id": "e_event", "source": "ev_x", "target": entry, "sign": sign}],
            "paths": [], "meta": {"entity_link": {"node": entry}}}


def _rec(headline, days_ago=0.0, simulated=False, **kw):
    return tracker.record_event(_resp(**kw), headline, ts=NOW - timedelta(days=days_ago), simulated=simulated)


def test_three_distinct_negative_stories_make_an_alert():
    _rec("Brent crude jumps as Red Sea shipping attacks resume", 3)
    assert tracker.compute_signals(now=NOW)["nodes"]["airmargin"]["level"] == "none"
    _rec("Oil prices climb on OPEC supply cut announcement", 2)
    assert tracker.compute_signals(now=NOW)["nodes"]["airmargin"]["level"] == "watch"
    _rec("Crude surges after refinery outage in Gulf region", 1)
    s = tracker.compute_signals(now=NOW)
    sig = s["nodes"]["airmargin"]
    assert sig["level"] == "alert" and sig["negative"] == 3 and s["alerts"] == ["airmargin"]
    assert sig["drivers"][0] == {"node": "crude", "shock_sign": 1, "count": 3}
    assert sig["stories"][0]["headline"].startswith("Crude surges") and "3 separate stories" in sig["reason"]
    assert s["nodes"]["banks"]["level"] == "none"                    # 'mixed' never alerts


def test_old_stories_fall_out_of_the_window():
    for i, h in enumerate(["Brent crude jumps as Red Sea attacks resume", "Oil climbs on OPEC supply cut news",
                           "Crude surges after refinery outage in Gulf"]):
        _rec(h, 20 + i)                                               # 3 weeks ago
    assert "airmargin" not in tracker.compute_signals(now=NOW)["nodes"]
    assert tracker.compute_signals(window_days=30, now=NOW)["nodes"]["airmargin"]["level"] == "alert"


def test_same_story_from_other_outlets_is_counted_once():
    assert _rec("Brent crude jumps as Red Sea shipping attacks resume", 0.5)
    assert not _rec("Brent crude jumps as Red Sea shipping attacks resume again", 0.2)   # near-identical headline
    assert tracker.compute_signals(now=NOW)["nodes"]["airmargin"]["negative"] == 1


def test_simulated_replays_count_but_can_be_excluded():
    for _ in range(3):
        assert _rec("Crude oil prices surge by 12% amid tensions", 0.1, simulated=True)   # replay repeats on purpose
    with_sim = tracker.compute_signals(now=NOW)
    assert with_sim["nodes"]["airmargin"]["level"] == "alert" and with_sim["nodes"]["airmargin"]["simulated_hits"] == 3
    assert "airmargin" not in tracker.compute_signals(include_simulated=False, now=NOW)["nodes"]


def test_canned_sample_is_never_recorded():
    assert not _rec("Anything", mode="mock")
    assert tracker.compute_signals(now=NOW)["events_in_window"] == 0


def test_trend_and_decayed_score():
    _rec("Brent crude jumps as Red Sea shipping attacks resume", 6)
    _rec("Oil climbs on OPEC supply cut announcement today", 0.5)
    _rec("Crude surges after refinery outage in Gulf region", 0.2)
    sig = tracker.compute_signals(now=NOW)["nodes"]["airmargin"]
    assert sig["trend"] == "rising" and 1.5 < sig["score"] < 3          # recent stories weigh more than the 6-day-old one


def test_direct_news_about_a_star_raises_a_watch():
    for h in ["Brent crude jumps as Red Sea shipping attacks resume", "Oil climbs on OPEC supply cut announcement",
              "Crude surges after refinery outage in Gulf region"]:
        _rec(h, 1, effects={})                                         # only the entry star, effect 'positive'
    sig = tracker.compute_signals(now=NOW)["nodes"]["crude"]
    assert sig["direct"] == 3 and sig["negative"] == 0 and sig["level"] == "watch"


def test_api_roundtrip_and_clear():
    for h in ["Brent crude jumps as Red Sea shipping attacks resume", "Oil climbs on OPEC supply cut announcement",
              "Crude surges after refinery outage in Gulf region"]:
        tracker.record_event(_resp(), h, ts=datetime.now(timezone.utc) - timedelta(hours=2))
    body = client.get("/api/recurrence").json()
    assert body["alerts"] == ["airmargin"] and body["thresholds"]["alert_hits"] == 3
    assert client.get("/api/recurrence?window_days=0").status_code == 422
    assert client.delete("/api/recurrence").json()["deleted"] == 3
    assert client.get("/api/recurrence").json()["alerts"] == []


def test_manual_analyze_feeds_the_tracker():
    news = ["Crude oil prices surge by 12% amid escalating geopolitical tensions in the Middle East.",
            "Brent crude jumps after OPEC announces deep production cuts for the next quarter.",
            "Oil climbs as pipeline outage in Libya tightens global supply this week."]
    for n in news:
        assert client.post("/api/analyze", json={"news": n, "simulated": True, "use_llm": False}).status_code == 200
    body = client.get("/api/recurrence").json()
    assert body["events_in_window"] == 3 and body["alerts"], body


def test_star_backtest_uses_the_recurring_driver(tmp_path, monkeypatch):
    import numpy as np
    import pandas as pd
    from app.quant import data_loader
    c = tmp_path / "cache"; c.mkdir()
    monkeypatch.setattr(data_loader, "CACHE_DIR", c)
    n = 1500; idx = pd.bdate_range("2018-01-01", periods=n); rng = np.random.default_rng(3)
    d = rng.normal(0, 0.01, n); m = rng.normal(0, 0.008, n); a = rng.normal(0, 0.006, n)
    for i in range(250, 1300, 150):
        d[i] = 0.09; a[i + 1:i + 6] -= 0.012
    for t, r in (("BZ=F", d), ("^NSEI", m), ("INDIGO.NS", a)):
        pd.DataFrame({"Date": idx.strftime("%Y-%m-%d"), "Close": 100 * np.exp(np.cumsum(r))}).to_csv(c / f"{t}.csv", index=False)
    for h in ["Brent crude jumps as Red Sea shipping attacks resume", "Oil climbs on OPEC supply cut announcement",
              "Crude surges after refinery outage in Gulf region"]:
        tracker.record_event(_resp(effects={"indigo": "negative"}), h, ts=datetime.now(timezone.utc) - timedelta(hours=3))
    out = client.get("/api/recurrence/indigo/backtest").json()
    assert out["available"] and out["driver"]["ticker"] == "BZ=F" and out["driver"]["direction"] == "up"
    t = out["targets"][0]
    assert t["node_id"] == "indigo" and t["n"] >= 3 and len(t["last_episodes"]) == 5
    miss = client.get("/api/recurrence/banks/backtest").json()
    assert miss["available"] is False and "No recurring news" in miss["reason"]


def test_memory_fallback_when_mongo_is_not_configured(monkeypatch):
    from app.graph import store
    monkeypatch.setattr(store.settings, "mongodb_uri", "")
    monkeypatch.setattr(tracker, "_memory", tracker._Memory())
    for h in ["Brent crude jumps as Red Sea shipping attacks resume", "Oil climbs on OPEC supply cut announcement",
              "Crude surges after refinery outage in Gulf region"]:
        assert tracker.record_event(_resp(), h, ts=NOW - timedelta(days=1))
    assert tracker.storage_kind() == "memory"
    assert tracker.compute_signals(now=NOW)["alerts"] == ["airmargin"]
    assert tracker.clear() == 3


def test_events_are_stored_in_mongodb_collection():
    from app.graph import store
    _rec("Brent crude jumps as Red Sea shipping attacks resume", 1)
    doc = store._collection("events_log").find_one({})
    assert doc["entry_node"] == "crude" and doc["shock_sign"] == 1 and doc["simulated"] is False and doc["nodes"][0]["id"] == "crude"


def test_mongo_outage_backs_off_and_never_breaks_analyze(monkeypatch):
    from app.graph import store
    calls = []

    def boom(name="analyses"):
        calls.append(1)
        raise ConnectionError("down")
    monkeypatch.setattr(store, "_collection", boom)
    r = client.post("/api/analyze", json={"news": "Crude oil prices surge by 12% amid tensions in the Middle East.", "use_llm": False, "simulated": True})
    assert r.status_code == 200 and "analysis_id" not in r.json()["meta"]      # analysis still works, just not saved
    n = len(calls)
    client.post("/api/analyze", json={"news": "Crude oil prices surge by 12% amid tensions in the Middle East.", "use_llm": False, "simulated": True})
    assert len(calls) == n                                                  # back-off: DB not hit again
    assert client.get("/api/recurrence").status_code == 503
