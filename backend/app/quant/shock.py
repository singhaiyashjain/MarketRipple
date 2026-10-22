"""Express a % move as a z-score vs the series' own volatility (rolling sigma). OWNER: M4"""
import numpy as np
import pandas as pd


def shock_zscore(prices: pd.Series, pct_move: float, window: int = 60) -> float:
    """z of a ONE-DAY move of `pct_move` percent vs the std of the last `window` daily log returns.
    Example: oil sigma ~2%/day -> a +12% move is ~5-6 sigma, i.e. extreme."""
    r = np.log(prices.dropna()).diff().dropna().tail(window)
    sigma = float(r.std())
    if len(r) < 20 or sigma == 0 or np.isnan(sigma):
        raise ValueError("not enough price history to estimate volatility")
    return float(np.log1p(pct_move / 100.0) / sigma)
