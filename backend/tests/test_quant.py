"""Quant tests on synthetic prices (no network). beta/shock/event_study need only pandas+numpy."""
import numpy as np
import pandas as pd
from app.quant.betas import estimate_beta
from app.quant.shock import shock_zscore
from app.quant.event_study import run_event_study
from app.quant.portfolio import scenario_pnl


def _series(seed=0, n=800, beta=0.5, lag=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    d = rng.normal(0, 0.02, n)
    a = np.roll(d, lag) * beta + rng.normal(0, 0.01, n)
    to_p = lambda r: pd.Series(100 * np.exp(np.cumsum(r)), index=idx)
    return to_p(d), to_p(a), to_p(rng.normal(0, 0.01, n))


def test_beta_recovers_known_relationship_and_lag():
    d, a, _ = _series(beta=0.5, lag=2)
    r = estimate_beta(d, a)
    assert abs(r["beta"] - 0.5) < 0.1 and r["lag_days"] == 2 and abs(r["t_stat"]) > 5
    assert r["stability"] in {"medium", "high"}


def test_beta_rejects_short_series():
    d, a, _ = _series(n=40)
    try:
        estimate_beta(d, a); assert False
    except ValueError:
        pass


def test_shock_zscore_scales_with_move():
    d, _, _ = _series()
    assert shock_zscore(d, 12) > shock_zscore(d, 3) > 0


def test_event_study_returns_structure():
    d, a, m = _series(beta=0.8)
    r = run_event_study(d, a, m, shock_sigma=2.0, shock_sign=1)
    assert r["n"] > 3 and set(r["car"]) <= {1, 5, 20}


def test_portfolio():
    out = scenario_pnl({"a": 0.5, "b": 0.5}, {"a": 1.0}, 10)
    assert out["pnl_pct"] == 5.0 and out["missing_beta"] == ["b"]
