"""Beta of asset to driver + lead-lag + stability. OWNER: M4
Daily log returns; for lag L in 0..max_lag regress asset[t+L] on driver[t] (OLS, numpy).
The best lag is chosen by |t|, which inflates significance a little (multiple lags tried), so
treat t-stats as indicative, not as proof - the UI note says so."""
import numpy as np
import pandas as pd


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if n < 10 or sxx == 0:
        return 0.0, 0.0, 0.0
    b = ((x - xm) * (y - ym)).sum() / sxx
    resid = y - (ym + b * (x - xm))
    se = np.sqrt((resid ** 2).sum() / (n - 2) / sxx)
    return float(b), float(se), float(b / se) if se > 0 else 0.0


def _returns(s: pd.Series) -> pd.Series:
    return np.log(s.dropna()).diff().dropna()


def estimate_beta(driver: pd.Series, asset: pd.Series, max_lag: int = 10) -> dict:
    """Return {beta, t_stat, n, lag_days, ci_low, ci_high, stability}"""
    d, a = _returns(driver), _returns(asset)
    df = pd.concat([d, a], axis=1, join="inner").dropna()
    df.columns = ["d", "a"]
    if len(df) < 60:
        raise ValueError("fewer than 60 overlapping daily returns")
    best = None
    for lag in range(0, max_lag + 1):
        x, y = df["d"].values[: len(df) - lag], df["a"].values[lag:]
        b, se, t = _ols(x, y)
        if best is None or abs(t) > abs(best[3]):
            best = (lag, b, se, t, len(x))
    lag, b, se, t, n = best
    x, y = df["d"].values[: len(df) - lag], df["a"].values[lag:]
    thirds = np.array_split(np.arange(len(x)), 3)           # stability: same sign in sub-periods?
    same = sum(1 for idx in thirds if np.sign(_ols(x[idx], y[idx])[0]) == np.sign(b))
    stability = {3: "high", 2: "medium"}.get(same, "low")
    return {"beta": round(b, 4), "t_stat": round(t, 2), "n": int(n), "lag_days": int(lag),
            "ci_low": round(b - 1.96 * se, 4), "ci_high": round(b + 1.96 * se, 4), "stability": stability}
