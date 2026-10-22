"""Entity alias normalisation. OWNER: M2  ("Brent","crude" -> "Crude Oil Prices")

normalize_entity(name)   -> canonical label (matches data/seed_nodes.json labels where possible)
entity_to_node_id(name)  -> seed node id (e.g. "crude") or None. Handy for graph.builder (M3)
                            to link the event node to the right seed node.
"""
import json
import re
from functools import lru_cache

from app.config import DATA_DIR

ALIASES: dict[str, str] = {
    # crude oil
    "brent": "Crude Oil Prices", "brent crude": "Crude Oil Prices", "wti": "Crude Oil Prices",
    "crude": "Crude Oil Prices", "crude oil": "Crude Oil Prices",
    "crude oil prices": "Crude Oil Prices", "crude prices": "Crude Oil Prices",
    "oil": "Crude Oil Prices", "oil prices": "Crude Oil Prices",
    # fuels
    "diesel": "Diesel Costs", "diesel prices": "Diesel Costs",
    "jet fuel": "Aviation Fuel Costs", "atf": "Aviation Fuel Costs",
    "aviation fuel": "Aviation Fuel Costs",
    # central bank / rates
    "rbi": "Reserve Bank of India", "reserve bank of india": "Reserve Bank of India",
    "reserve bank": "Reserve Bank of India",
    "repo rate": "Policy Interest Rate", "policy rate": "Policy Interest Rate",
    "policy repo rate": "Policy Interest Rate", "interest rate": "Policy Interest Rate",
    "interest rates": "Policy Interest Rate",
    "bond yield": "Bond Yields", "bond yields": "Bond Yields",
    # currency
    "rupee": "USD/INR", "indian rupee": "USD/INR", "inr": "USD/INR",
    "usd/inr": "USD/INR", "usdinr": "USD/INR", "dollar-rupee": "USD/INR",
    # macro
    "inflation": "Inflationary Pressure", "cpi": "Inflationary Pressure",
    "fii": "Foreign Portfolio Flows", "fpi": "Foreign Portfolio Flows",
    "foreign investors": "Foreign Portfolio Flows",
    "current account deficit": "Current Account Deficit", "cad": "Current Account Deficit",
    # markets / sectors
    "nifty": "Nifty 50", "nifty 50": "Nifty 50", "nifty50": "Nifty 50",
    "banks": "Banks", "banking": "Banks", "banking sector": "Banks",
    "real estate": "Real Estate", "realty": "Real Estate",
}


def _clean(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w/\s&'-]", " ", name.lower())).strip()


def normalize_entity(name: str) -> str:
    """Canonical label for an entity name; unknown names are returned stripped, unchanged."""
    if not name:
        return name
    cleaned = _clean(name)
    if cleaned in ALIASES:
        return ALIASES[cleaned]
    # seed labels match themselves case-insensitively
    return _seed_labels().get(cleaned, name.strip())


@lru_cache(maxsize=1)
def _seed_labels() -> dict[str, str]:
    """{cleaned label -> label} from data/seed_nodes.json (empty if file missing)."""
    try:
        nodes = json.loads((DATA_DIR / "seed_nodes.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {_clean(n["label"]): n["label"] for n in nodes if "label" in n}


@lru_cache(maxsize=1)
def _label_to_id() -> dict[str, str]:
    try:
        nodes = json.loads((DATA_DIR / "seed_nodes.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {n["label"]: n["id"] for n in nodes if "id" in n and "label" in n}


def entity_to_node_id(name: str) -> str | None:
    """Map any alias/label to a seed node id, or None if it isn't in the seed graph."""
    return _label_to_id().get(normalize_entity(name))
