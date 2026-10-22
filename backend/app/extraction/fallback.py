"""Offline rule-based extractor (regex/keywords). Must work with no internet. OWNER: M2
Covers the 3 demo scenarios: crude-oil shock, central-bank rate move, INR move.
Anything else -> event_type "other" (the graph builder then has nothing to link; that is
reported honestly rather than guessed)."""
import re

from app.schemas import ExtractedEvent

_UP = r"surge[sd]?|surging|rise[sn]?|rising|rose|jump(?:s|ed|ing)?|climb(?:s|ed|ing)?|spik(?:e|es|ed|ing)|soar(?:s|ed|ing)?|rall(?:y|ies|ied)|gain(?:s|ed)?|hike[sd]?|raise[sd]?|increase[sd]?|higher"
_DOWN = r"fall[s]?|fell|falling|drop(?:s|ped|ping)?|plunge[sd]?|plunging|slump(?:s|ed|ing)?|declin(?:e|es|ed|ing)|tumbl(?:e|es|ed|ing)|slid(?:e|es|ing)?|crash(?:es|ed|ing)?|sink[s]?|sank|cut[s]?|lower(?:s|ed)?|reduce[sd]?|weaken(?:s|ed|ing)?|deprecia\w+|lower"

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|per\s?cent|percent)", re.I)
_BPS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:basis\s+points?|bps|bp)\b", re.I)
_DATE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b",
    re.I)
_DRIVERS = [
    re.compile(r"\bto\s+(?:curb|contain|control|tame|check)\s+([^,.;]+)", re.I),
    re.compile(r"\bamid\s+([^,.;]+)", re.I),
    re.compile(r"\b(?:due\s+to|owing\s+to|driven\s+by|on\s+account\s+of)\s+([^,.;]+)", re.I),
    re.compile(r"\bciting\s+([^,.;]+)", re.I),
    re.compile(r"(?<!well )(?<!such )\bas\s+((?:[a-z]+\s+){1,}[^,.;]+)", re.I),
    re.compile(r"\bfollowing\s+([^,.;]+)", re.I),
]


def _direction(text: str) -> str:
    """Direction word that appears first in the text (up vs down)."""
    up = re.search(rf"\b(?:{_UP})\b", text, re.I)
    down = re.search(rf"\b(?:{_DOWN})\b", text, re.I)
    if up and down:
        return "increase" if up.start() < down.start() else "decrease"
    if up:
        return "increase"
    if down:
        return "decrease"
    return "unknown"


def _driver(text: str) -> str | None:
    for pat in _DRIVERS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def _country(text: str) -> str | None:
    if re.search(r"\b(india|indian|rbi|rupee|inr|nifty|sensex)\b", text, re.I):
        return "India"
    if re.search(r"\b(federal reserve|the fed|fomc|u\.?s\.? treasury)\b", text, re.I):
        return "United States"
    return None


def _date(text: str) -> str | None:
    m = _DATE.search(text)
    return m.group(1) if m else None


def rule_based_extract(news: str) -> ExtractedEvent:
    text = " ".join(news.split())
    common = dict(driver=_driver(text), country=_country(text), event_date=_date(text))
    pct = _PCT.search(text)
    bps = _BPS.search(text)

    # 1) central-bank rate decision (checked first: "raises repo rate ... fuel prices" mentions oil words)
    if re.search(r"\b(repo rate|policy rate|interest rates?|rate (?:hike|cut)|basis points?|bps)\b", text, re.I) \
            and re.search(r"\b(rbi|reserve bank|federal reserve|the fed|fomc|central bank|mpc)\b", text, re.I):
        d = _direction(text)
        is_fed = re.search(r"\b(federal reserve|the fed|fomc)\b", text, re.I)
        change = None
        if bps:
            sign = "-" if d == "decrease" else "+"
            change = f"{sign}{bps.group(1)} basis points"
        return ExtractedEvent(
            event_type="interest_rate_cut" if d == "decrease" else "interest_rate_hike" if d == "increase" else "other",
            entity="US Federal Reserve" if is_fed else "Reserve Bank of India",
            indicator="policy_interest_rate" if is_fed else "policy_repo_rate",
            direction=d, change=change, change_pct=None, **common)

    # 2) rupee move vs 3) crude oil: if a text mentions both, the one named first is the headline
    inr = re.search(r"\b(rupee|inr)\b", text, re.I)
    oil = re.search(r"\b(crude|brent|wti|oil prices?|oil)\b", text, re.I)
    if inr and not (oil and oil.start() < inr.start()):
        # entity is the pair; rupee falling => USD/INR increases
        weak = re.search(r"\b(fall[s]?|fell|slump\w*|weaken\w*|deprecia\w+|record low|slide[s]?|plunge\w*|sink\w*|tumbl\w+)\b", text, re.I)
        strong = re.search(r"\b(strengthen\w*|apprecia\w+|gain[s]?|rall(?:y|ies|ied)|rise[s]?|rose|surge[sd]?)\b", text, re.I)
        if weak and not (strong and strong.start() < weak.start()):
            d, et = "increase", "currency_depreciation"
        elif strong:
            d, et = "decrease", "currency_appreciation"
        else:
            d, et = "unknown", "other"
        change = f"{'+' if d == 'increase' else '-'}{pct.group(1)}%" if pct else None
        return ExtractedEvent(event_type=et, entity="USD/INR", indicator="usd_inr_exchange_rate",
                              direction=d, change=change,
                              change_pct=float(pct.group(1)) if pct else None, **common)

    if oil:
        d = _direction(text)
        change = f"{'-' if d == 'decrease' else '+'}{pct.group(1)}%" if pct else None
        return ExtractedEvent(event_type="commodity_price_shock", entity="Crude Oil Prices",
                              indicator="crude_oil_price", direction=d, change=change,
                              change_pct=float(pct.group(1)) if pct else None, **common)

    # 4) nothing we can recognise offline
    return ExtractedEvent(event_type="other", entity="Unclassified financial event",
                          indicator=None, direction="unknown", change=None, change_pct=None,
                          **common)
