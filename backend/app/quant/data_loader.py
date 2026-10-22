"""Load cached price series (data/cache/*.csv); fetch via scripts/fetch_prices.py. OWNER: M4
Tickers map: data/tickers.json (node id -> yfinance ticker). Always work OFFLINE from cache.
CSV format: Date,Close  (one file per ticker, named <ticker>.csv)."""
import json
import pandas as pd
from app.config import DATA_DIR

CACHE_DIR = DATA_DIR / "cache"
_MEM: dict[str, tuple[float, pd.Series]] = {}      # ticker -> (file mtime, parsed series): parse each CSV once


def ticker_for(node_id: str) -> str | None:
    t = json.loads((DATA_DIR / "tickers.json").read_text(encoding="utf-8"))
    return t.get(node_id) if not node_id.startswith("_") else None


def cache_available() -> bool:
    return CACHE_DIR.exists() and any(CACHE_DIR.glob("*.csv"))


def load_prices(ticker: str) -> pd.Series:
    """Daily close as a float Series indexed by date. FileNotFoundError if not cached."""
    path = CACHE_DIR / f"{ticker}.csv"
    if not path.exists():
        raise FileNotFoundError(f"no cached prices for {ticker}; run scripts/fetch_prices.py")
    key = f"{path}"
    mtime = path.stat().st_mtime
    hit = _MEM.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    df = pd.read_csv(path, dtype={"Date": str}).dropna(subset=["Close"])
    # first 10 chars = YYYY-MM-DD; robust to "2020-01-01 00:00:00+05:30" style stamps (no tz shifting)
    dates = pd.to_datetime(df["Date"].astype(str).str[:10], errors="coerce")
    ok = dates.notna()
    s = pd.Series(df.loc[ok, "Close"].astype(float).values, index=pd.DatetimeIndex(dates[ok]), name=ticker)
    s = s[~s.index.duplicated()].sort_index()
    s = s[s > 0]                                    # log-returns need positive prices
    _MEM[key] = (mtime, s)
    return s
