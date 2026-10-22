"""Event study: cumulative abnormal return of an asset after past driver shocks. OWNER: M4
Market model: r_asset = a + b*r_market ; AR = r - (a + b*r_mkt) ; CAR over [0,+1,+5,+20].
Shock = driver daily return with |z| >= shock_sigma vs its prior 60-day volatility.
Only the direction-matched events are returned for `sign`: pass shock_sign=+1 for rises.

Additive extras (existing callers are unaffected):
  min_gap  - shocks closer than this many trading days are merged into one episode (the first one is kept).
  episodes - per-episode detail: date, driver move, raw return and abnormal return (CAR) at each window."""
import numpy as np
import pandas as pd


def run_event_study(driver: pd.Series, asset: pd.Series, market: pd.Series,
                    shock_sigma: float = 2.0, windows=(1, 5, 20), shock_sign: int = 0,
                    min_gap: int = 0) -> dict:
    """Return {n, car:{window: mean}, t_stat:{window: t}, event_dates:[...], episodes:[...]}"""
    r = pd.concat([np.log(driver).diff(), np.log(asset).diff(), np.log(market).diff()],
                  axis=1, join="inner").dropna()
    r.columns = ["d", "a", "m"]
    vol = r["d"].rolling(60).std().shift(1)
    z = r["d"] / vol
    mask = z.abs() >= shock_sigma
    if shock_sign:
        mask &= np.sign(z) == shock_sign
    cars: dict[int, list[float]] = {w: [] for w in windows}
    dates = []
    episodes = []
    last_kept = -10**9
    for i in np.flatnonzero(mask.values):
        if min_gap and i - last_kept < min_gap:             # same episode as the previous shock
            continue
        lo = i - 120
        if lo < 0 or i + max(windows) >= len(r):
            continue
        est = r.iloc[lo:i - 5]                              # estimation window, excludes the event run-up
        if len(est) < 60 or est["m"].var() == 0:
            continue
        last_kept = i
        b = est["a"].cov(est["m"]) / est["m"].var()
        alpha = est["a"].mean() - b * est["m"].mean()
        ar = r["a"] - (alpha + b * r["m"])
        ep = {"date": str(r.index[i].date()), "z": round(float(z.iloc[i]), 2),
              "driver_move_pct": round(float(np.expm1(r["d"].iloc[i])) * 100, 2),
              "car": {}, "raw": {}}
        for w in windows:
            c = float(ar.iloc[i:i + w + 1].sum())
            cars[w].append(c)
            ep["car"][w] = round(c, 5)
            ep["raw"][w] = round(float(np.expm1(r["a"].iloc[i:i + w + 1].sum())), 5)
        dates.append(ep["date"])
        episodes.append(ep)
    out = {"n": len(dates), "car": {}, "t_stat": {}, "event_dates": dates, "episodes": episodes}
    for w, v in cars.items():
        if len(v) >= 3:
            arr = np.array(v)
            out["car"][w] = round(float(arr.mean()), 5)
            sd = arr.std(ddof=1)
            out["t_stat"][w] = round(float(arr.mean() / (sd / np.sqrt(len(arr)))), 2) if sd > 0 else 0.0
    return out
