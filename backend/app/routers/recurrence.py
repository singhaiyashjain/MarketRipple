"""Recurring-news alerts + star backtest: /api/recurrence/*  and  POST /api/backtest.  OWNER: M4"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.graph import store
from app.quant import data_loader
from app.quant.backtest import backtest_analysis
from app.recurrence import tracker

router = APIRouter()


@router.get("/recurrence")
def recurrence(window_days: float | None = None, include_simulated: bool = True):
    """Per-star recurrence signals (alerts blink in the UI). window_days defaults to the server setting."""
    if window_days is not None and not 0.04 <= window_days <= 120:
        raise HTTPException(status_code=422, detail="window_days must be between 1 hour and 120 days")
    try:
        out = tracker.public_signals(window_days=window_days, include_simulated=include_simulated)
    except Exception:
        raise HTTPException(status_code=503, detail="recurring-news storage (MongoDB) unavailable")
    out["storage"] = tracker.storage_kind()
    return out


@router.get("/recurrence/{node_id}/backtest")
def star_backtest(node_id: str, window_days: float | None = None, include_simulated: bool = True):
    """'The last 5 times this happened' for the shock that keeps hitting this star."""
    try:
        return tracker.star_backtest(node_id, window_days, include_simulated)
    except Exception:
        raise HTTPException(status_code=503, detail="recurring-news storage (MongoDB) unavailable")


@router.delete("/recurrence")
def clear_history(simulated_only: bool = False):
    try:
        return {"deleted": tracker.clear(simulated_only)}
    except Exception:
        raise HTTPException(status_code=503, detail="recurring-news storage (MongoDB) unavailable")


class BacktestBody(BaseModel):
    analysis_id: str | int | None = None
    analysis: dict | None = None
    shock_sigma: float = 2.0


@router.post("/backtest")
def backtest(body: BacktestBody):
    """Historical backtest for an analysis (by saved id, or the full response object)."""
    if body.analysis_id is not None:
        try:
            resp = store.load_analysis(str(body.analysis_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="analysis not found")
        except Exception:                                # storage off: use the full analysis if the client sent it
            if not body.analysis:
                raise HTTPException(status_code=503, detail="analysis storage unavailable; send the full analysis")
            resp = body.analysis
    elif body.analysis:
        resp = body.analysis
    else:
        raise HTTPException(status_code=422, detail="send analysis_id or analysis")
    if not 1.0 <= body.shock_sigma <= 4.0:
        raise HTTPException(status_code=422, detail="shock_sigma must be between 1 and 4")
    if not data_loader.cache_available():
        return {"available": False, "reason": "No price history cached yet. Run: python scripts/fetch_prices.py",
                "caveat": "Historical co-movement of proxy tickers, small sample, not a prediction or proof of causation."}
    return backtest_analysis(resp, shock_sigma=body.shock_sigma)
