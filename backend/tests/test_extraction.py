"""M2 tests - no network needed (LLM is monkeypatched)."""
import json

import pytest

from app.config import DATA_DIR
from app.extraction import extractor, llm_client
from app.extraction.fallback import rule_based_extract
from app.extraction.normalizer import entity_to_node_id, normalize_entity

SAMPLES = {s["id"]: s["news"] for s in json.loads((DATA_DIR / "sample_events.json").read_text(encoding="utf-8"))}


def test_oil_extraction_fallback():
    ev = rule_based_extract(SAMPLES["oil_shock"])
    assert ev.event_type == "commodity_price_shock"
    assert ev.entity == "Crude Oil Prices" and ev.direction == "increase"
    assert ev.change_pct == 12.0 and ev.change == "+12%"
    assert "geopolitical" in ev.driver.lower()
    assert ev.event_date is None            # never invented


def test_rate_hike_extraction_fallback():
    ev = rule_based_extract(SAMPLES["rate_hike"])
    assert ev.event_type == "interest_rate_hike" and ev.direction == "increase"
    assert ev.entity == "Reserve Bank of India" and ev.country == "India"
    assert ev.change == "+25 basis points" and ev.change_pct is None
    assert "inflation" in ev.driver.lower()


def test_inr_depreciation_extraction_fallback():
    ev = rule_based_extract(SAMPLES["inr_depreciation"])
    assert ev.event_type == "currency_depreciation"
    assert ev.entity == "USD/INR" and ev.direction == "increase"   # rupee weaker => USD/INR up
    assert ev.change is None and ev.change_pct is None              # no number in the text


def test_unrecognised_text_is_other():
    ev = rule_based_extract("The company announced a new office opening in Pune next quarter.")
    assert ev.event_type == "other"


def test_normalizer():
    assert normalize_entity("Brent") == "Crude Oil Prices"
    assert normalize_entity("  RBI ") == "Reserve Bank of India"
    assert normalize_entity("Something Unknown") == "Something Unknown"
    assert entity_to_node_id("Brent crude") == "crude"
    assert entity_to_node_id("rupee") == "usdinr"
    assert entity_to_node_id("Something Unknown") is None


def test_llm_path_normalises_and_grounds(monkeypatch):
    fake = {"event_type": "commodity_price_shock", "entity": "Brent", "indicator": "crude_oil_price",
            "direction": "increase", "change": "+12%", "change_pct": 40.0,   # 40 is NOT in the text
            "driver": "geopolitical tensions", "country": None,
            "event_date": "2031-01-01", "source": None}                      # date NOT in the text
    monkeypatch.setattr(llm_client, "complete_json", lambda prompt, schema_hint=None: fake)
    ev, mode, warnings = extractor.extract_with_status(SAMPLES["oil_shock"], use_llm=True)
    assert mode == "live"
    assert ev.entity == "Crude Oil Prices"
    assert ev.change_pct is None and ev.event_date is None
    assert ev.change == "+12%"                                                # 12 IS in the text
    assert len(warnings) == 2


def test_llm_failure_falls_back(monkeypatch):
    def boom(prompt, schema_hint=None):
        raise llm_client.LLMUnavailable("down")
    monkeypatch.setattr(llm_client, "complete_json", boom)
    ev, mode, warnings = extractor.extract_with_status(SAMPLES["rate_hike"], use_llm=True)
    assert mode == "fallback" and ev.event_type == "interest_rate_hike" and warnings


def test_bad_llm_json_falls_back(monkeypatch):
    monkeypatch.setattr(llm_client, "complete_json", lambda p, schema_hint=None: {"foo": "bar"})
    ev, mode, _ = extractor.extract_with_status(SAMPLES["oil_shock"], use_llm=True)
    assert mode == "fallback" and ev.entity == "Crude Oil Prices"


def test_use_llm_false_never_calls_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called")
    monkeypatch.setattr(llm_client, "complete_json", boom)
    assert extractor.extract_event(SAMPLES["oil_shock"], use_llm=False).entity == "Crude Oil Prices"


def test_parse_json_text_handles_fences():
    assert llm_client.parse_json_text('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm_client.parse_json_text('Sure! {"a": [1, 2]} hope that helps') == {"a": [1, 2]}
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.parse_json_text("no json here")
