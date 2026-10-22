"""POST /api/chat - grounded AI analyst.  OWNER: M2"""
import logging
from typing import Literal, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chat.analyst import answer_question
from app.graph import store
from app.quant import data_loader
from app.quant.backtest import backtest_analysis

router = APIRouter()
log = logging.getLogger("finpulse.chat")


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = []
    analysis_id: Optional[Union[str, int]] = None
    analysis: Optional[dict] = None
    backtest: Optional[dict] = None
    language: Optional[Literal["en", "hi"]] = None


@router.post("/chat")
def chat(body: ChatBody):
    """Answer a question about the current analysis. Prefers analysis_id, accepts the full analysis as a fallback."""
    analysis = None
    if body.analysis_id is not None:
        try:
            analysis = store.load_analysis(str(body.analysis_id))
        except Exception:                              # unknown id, or MongoDB off: fall back to the analysis object
            analysis = None
    analysis = analysis or body.analysis
    if not analysis or not analysis.get("nodes"):
        raise HTTPException(status_code=422, detail="send analysis_id or analysis")
    backtest = body.backtest
    if backtest is None and data_loader.cache_available():       # so "has this happened before?" works without the client sending it
        try:
            backtest = backtest_analysis(analysis)
        except Exception:
            log.exception("backtest for chat failed")
    signals = None
    try:
        from app.recurrence import tracker
        signals = tracker.public_signals()
    except Exception:
        pass
    return answer_question(body.message, analysis, [t.model_dump() for t in body.history], backtest, body.language, signals)
