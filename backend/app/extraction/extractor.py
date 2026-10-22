"""News text -> ExtractedEvent.  OWNER: M2
Rules: validate with Pydantic; NEVER invent dates/numbers absent from the source.
Flow: try LLM (llm_client.complete_json) -> on failure/use_llm=False use fallback.rule_based_extract.

extract_event(news, use_llm)            -> ExtractedEvent                 (what pipeline.py calls)
extract_with_status(news, use_llm)      -> (event, mode, warnings)        (mode: "live" | "fallback";
                                           M3 can use this to set AnalyzeResponse.mode / warnings)
"""
import re
from typing import Literal

from app.extraction import llm_client
from app.extraction.fallback import rule_based_extract
from app.extraction.normalizer import normalize_entity
from app.extraction.prompts import EVENT_TYPES, EXTRACT_PROMPT
from app.schemas import ExtractedEvent

_DIRECTIONS = {"increase", "decrease", "unchanged", "unknown"}


def _numbers_in(text: str) -> set[float]:
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))}


def _ground(ev: ExtractedEvent, news: str) -> list[str]:
    """Null out anything the LLM states that the source text does not contain. Returns warnings."""
    warnings: list[str] = []
    nums = _numbers_in(news)
    if ev.change_pct is not None and ev.change_pct not in nums:
        warnings.append(f"Dropped change_pct {ev.change_pct}: not found in the source text.")
        ev.change_pct = None
    if ev.change and not (_numbers_in(ev.change) & nums):
        warnings.append(f"Dropped change '{ev.change}': not found in the source text.")
        ev.change = None
    if ev.event_date:
        years = re.findall(r"\b(?:19|20)\d{2}\b", ev.event_date)
        if not years or not all(y in news for y in years):
            warnings.append(f"Dropped event_date '{ev.event_date}': not found in the source text.")
            ev.event_date = None
    return warnings


def _from_llm(news: str) -> ExtractedEvent:
    prompt = EXTRACT_PROMPT.format(event_types=", ".join(EVENT_TYPES), news=news)
    data = llm_client.complete_json(prompt)
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise llm_client.LLMUnavailable("LLM returned no JSON object")
    data = {k: v for k, v in data.items() if v not in ("", "null", "None")}
    if data.get("direction") not in _DIRECTIONS:
        data["direction"] = "unknown"
    if data.get("event_type") not in EVENT_TYPES:
        data["event_type"] = "other"
    if isinstance(data.get("change_pct"), str):
        try:
            data["change_pct"] = float(data["change_pct"].strip("%+ "))
        except ValueError:
            data["change_pct"] = None
    data.pop("is_simulated", None)  # pipeline owns this flag
    ev = ExtractedEvent(**data)     # raises if event_type/entity missing -> caller falls back
    ev.entity = normalize_entity(ev.entity)
    return ev


def extract_with_status(news: str, use_llm: bool = True) -> tuple[ExtractedEvent, Literal["live", "fallback"], list[str]]:
    warnings: list[str] = []
    if use_llm:
        try:
            ev = _from_llm(news)
            warnings += _ground(ev, news)
            return ev, "live", warnings
        except Exception as exc:  # LLM down, bad JSON, schema mismatch -> deterministic path
            warnings.append(f"LLM extraction unavailable ({type(exc).__name__}: {str(exc)[:150]}); used rule-based extractor.")
    ev = rule_based_extract(news)
    ev.entity = normalize_entity(ev.entity)
    if ev.event_type == "other":
        warnings.append("Rule-based extractor did not recognise this event type.")
    return ev, "fallback", warnings


def extract_event(news: str, use_llm: bool = True) -> ExtractedEvent:
    return extract_with_status(news, use_llm)[0]
