"""Backtest tests on SYNTHETIC prices with known shock dates (no network, no LLM)."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quant import backtest, data_loader

client = TestClient(app)
N = 1500
IDX = pd.bdate_range("2018-01-01", periods=N)
SHOCKS = [300, 450, 600, 750, 900, 1050, 1200]            # driver +8% days, far apart
CLOSE_PAIR = (1300, 1303)                                  # two shocks 3 days apart -> must merge into ONE episode


def _px(r):
    return pd.Series(100 * np.exp(np.cumsum(r)), index=IDX)


def _write(cache, ticker, series):
    pd.DataFrame({"Date": series.index.strftime("%Y-%m-%d"), "Close": series.values}).to_csv(cache / f"{ticker}.csv", index=False)


@pytest.fixture
def cache(tmp_path, monkeypatch):
    c = tmp_path / "cache"
    c.mkdir()
    monkeypatch.setattr(data_loader, "CACHE_DIR", c)
    rng = np.random.default_rng(7)
    d = rng.normal(0, 0.01, N)
    mkt = rng.normal(0, 0.008, N)
    for i in SHOCKS + list(CLOSE_PAIR):
        d[i] = 0.08
    d[1100] = -0.08                                        # a DOWN shock: must be ignored for a rise
    a = rng.normal(0, 0.006, N) + 0.3 * mkt                # banks: falls ~1%/day for 5 days after every rise shock
    for i in SHOCKS + [CLOSE_PAIR[0]]:
        a[i + 1:i + 6] -= 0.01
    o = rng.normal(0, 0.006, N) + 0.3 * mkt                # omc: unaffected noise
    _write(c, "BZ=F", _px(d))
    _write(c, "^NSEI", _px(mkt))
    _write(c, "^NSEBANK", _px(a))
    _write(c, "BPCL.NS", _px(o))
    return c


def _bt(a):
    """4-sigma on purpose: with 1% daily noise, ordinary 2-sigma days happen by chance; only the injected 8% shocks pass 4."""
    return backtest.backtest_analysis(a, shock_sigma=4.0)


def _analysis(entry="crude", sign=1, effect_banks="negative", change_pct=None):
    nodes = [{"id": "ev_oil", "label": "Oil up", "type": "event", "effect": "neutral"},
             {"id": entry, "label": "Crude Oil Prices", "type": "commodity", "effect": "positive"},
             {"id": "banks", "label": "Banks", "type": "sector", "effect": effect_banks},
             {"id": "omc", "label": "OMCs", "type": "company", "effect": "negative"},
             {"id": "avfuel", "label": "Aviation fuel", "type": "indicator", "effect": "negative"}]
    return {"mode": "live", "event": {"direction": "increase", "change_pct": change_pct, "is_simulated": False},
            "nodes": nodes,
            "edges": [{"id": "e_event", "source": "ev_oil", "target": entry, "sign": sign}],
            "paths": [{"id": "p1", "node_ids": ["ev_oil", entry, "banks"], "strength": 0.5},
                      {"id": "p2", "node_ids": ["ev_oil", entry, "avfuel", "omc"], "strength": 0.3}],
            "meta": {"entity_link": {"node": entry}}}


def test_finds_the_known_shock_dates_and_merges_close_ones(cache):
    out = _bt(_analysis())
    assert out["available"]
    banks = next(t for t in out["targets"] if t["node_id"] == "banks")
    got = {e["date"] for e in banks["last_episodes"]}
    # 5 most recent episodes, newest first: close pair merged into 1 (keeps the first), down-shock at 1100 ignored
    expected = [IDX[i].strftime("%Y-%m-%d") for i in (1300, 1200, 1050, 900, 750)]
    assert [e["date"] for e in banks["last_episodes"]] == expected
    assert IDX[1303].strftime("%Y-%m-%d") not in got and IDX[1100].strftime("%Y-%m-%d") not in got
    assert banks["n"] == len(SHOCKS) + 1                            # 7 separate shocks + the merged pair


def test_affected_asset_shows_negative_abnormal_return_and_agrees_with_graph(cache):
    out = _bt(_analysis())
    banks = next(t for t in out["targets"] if t["node_id"] == "banks")
    assert banks["predicted"] == "down"
    assert banks["stats"]["mean_abnormal_pct"]["5"] < -2.0         # ~-5% injected
    assert banks["hit_rate"]["5"] >= 0.8
    assert banks["agrees"] is True and banks["significant"] is True
    ep = banks["last_episodes"][0]
    assert set(ep["returns"]) == {"1", "5", "20"} and ep["returns"]["5"]["abnormal_pct"] < 0
    assert out["caveat"].startswith("Historical co-movement") and out["date_range"]["start"] <= out["date_range"]["end"]


def test_history_disagrees_when_graph_predicts_the_wrong_way(cache):
    out = _bt(_analysis(effect_banks="positive"))
    banks = next(t for t in out["targets"] if t["node_id"] == "banks")
    assert banks["agrees"] is False


def test_unrelated_asset_is_not_called_in_agreement(cache):
    out = _bt(_analysis())
    omc = next(t for t in out["targets"] if t["node_id"] == "omc")
    assert omc["significant"] is False and omc["agrees"] is None      # noise never counts as agreement


def test_down_shocks_for_a_decrease(cache):
    out = _bt(_analysis(sign=-1))
    banks = next(t for t in out["targets"] if t["node_id"] == "banks")
    assert banks["n"] < 3 and banks["stats"] is None and "Insufficient history" in banks["note"]   # only one down shock exists


def test_size_comparison_only_when_the_news_states_a_size(cache):
    assert "size_comparison" not in _bt(_analysis())
    sc = _bt(_analysis(change_pct=12.0))["size_comparison"]
    assert sc["stated_pct"] == 12.0 and sc["share_of_history_smaller"] == 1.0 and 7 < sc["median_historical_move_pct"] < 9


def test_missing_driver_ticker_is_reported_not_faked(cache):
    out = _bt(_analysis(entry="inflation"))      # no ticker for 'inflation'
    assert out["available"] is False and "no price proxy" in out["reason"]


def test_missing_csv_is_reported(cache):
    (cache / "BZ=F.csv").unlink()
    out = _bt(_analysis())
    assert out["available"] is False and "BZ=F" in out["reason"]


def test_targets_without_data_or_sharing_driver_ticker_are_skipped(cache):
    a = _analysis()
    a["nodes"].append({"id": "upstream", "label": "Upstream", "type": "indicator", "effect": "positive"})   # ONGC.NS: no csv
    a["paths"].append({"id": "p3", "node_ids": ["ev_oil", "crude", "upstream"], "strength": 0.2})
    out = _bt(a)
    reasons = {s["node_id"]: s["reason"] for s in out["skipped"]}
    assert "no cached prices" in reasons["upstream"] and "no price proxy" in reasons["avfuel"]


def test_unknown_direction_is_unavailable(cache):
    a = _analysis(); a["edges"] = []; a["event"]["direction"] = "unknown"
    assert _bt(a)["available"] is False


def test_endpoint_with_full_analysis_object(cache):
    r = client.post("/api/backtest", json={"analysis": _analysis(), "shock_sigma": 4.0})
    assert r.status_code == 200 and r.json()["available"] is True
    assert client.post("/api/backtest", json={}).status_code == 422
    assert client.post("/api/backtest", json={"analysis_id": 999999}).status_code == 404


def test_endpoint_without_any_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "CACHE_DIR", tmp_path / "empty")
    r = client.post("/api/backtest", json={"analysis": _analysis()})
    assert r.json()["available"] is False and "fetch_prices" in r.json()["reason"]


def test_loader_handles_timezone_stamped_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "CACHE_DIR", tmp_path)
    (tmp_path / "X.csv").write_text("Date,Close\n2020-01-01 00:00:00+05:30,10\n2020-01-02 00:00:00+05:30,11\n")
    s = data_loader.load_prices("X")
    assert [str(d.date()) for d in s.index] == ["2020-01-01", "2020-01-02"]


def test_real_cache_if_present():
    """Runs only on a machine that has run scripts/fetch_prices.py: oil rise and USD/INR rise give real episodes."""
    if not (data_loader.CACHE_DIR / "BZ=F.csv").exists():
        pytest.skip("data/cache not present in this environment")
    for entry, tgt in (("crude", "banks"), ("usdinr", "it_rev")):
        out = backtest.backtest_pair(entry, 1, [{"id": tgt, "label": tgt, "effect": "negative"}])
        assert out["available"] and out["targets"][0]["n"] >= 3
