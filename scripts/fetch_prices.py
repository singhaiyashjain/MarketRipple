"""Download daily prices for tickers in data/tickers.json into data/cache/<ticker>.csv. OWNER: M4
Run on a machine with internet:  pip install yfinance && python scripts/fetch_prices.py
Then COMMIT data/cache/ so the app works offline. Failed tickers are listed, never faked."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"


def main() -> None:
    import yfinance as yf
    tickers = json.loads((ROOT / "data" / "tickers.json").read_text(encoding="utf-8"))
    symbols = sorted({v for k, v in tickers.items() if not k.startswith("_")})
    CACHE.mkdir(parents=True, exist_ok=True)
    failed = []
    for sym in symbols:
        try:
            df = yf.download(sym, period="10y", auto_adjust=True, progress=False)
            close = df["Close"].squeeze().dropna()
            if len(close) < 250:
                raise ValueError(f"only {len(close)} rows")
            close.rename("Close").rename_axis("Date").to_csv(CACHE / f"{sym}.csv")
            print(f"ok   {sym:14s} {len(close)} rows")
        except Exception as exc:                      # keep going; report at the end
            failed.append(sym)
            print(f"FAIL {sym:14s} {exc}")
    print(f"\n{len(symbols) - len(failed)}/{len(symbols)} cached. Failed: {failed or 'none'}")


if __name__ == "__main__":
    main()
