"""AI analyst: context, id validation, number guard, template fallback, Hindi, endpoint. LLM is mocked (no network)."""
import pytest
from fastapi.testclient import TestClient

from app.chat import analyst
from app.extraction import llm_client
from app.main import app

client = TestClient(app)


def _analysis():
    nodes = [{"id": "ev_oil", "label": "Oil +12%", "type": "event", "effect": "neutral"},
             {"id": "crude", "label": "Crude Oil Prices", "type": "commodity", "effect": "positive"},
             {"id": "airmargin", "label": "Airline Profit Margins", "type": "indicator", "effect": "negative"},
             {"id": "banks", "label": "Banks", "type": "sector", "effect": "mixed"}]
    edges = [{"id": "e_event", "source": "ev_oil", "target": "crude", "sign": 1, "weight": 1.0, "evidence_type": "news_evidence", "verification_status": "supported"},
             {"id": "e1", "source": "crude", "target": "airmargin", "sign": -1, "weight": 0.7, "evidence_type": "llm_inferred", "verification_status": "unverified"},
             {"id": "e2", "source": "crude", "target": "banks", "sign": 0, "weight": 0.3, "evidence_type": "domain_rule", "verification_status": "reviewed",
              "stats": {"beta": 0.12, "t_stat": 2.4, "n": 800}}]
    paths = [{"id": "p1", "node_ids": ["ev_oil", "crude", "airmargin"], "edge_ids": ["e_event", "e1"], "strength": 0.7, "terminal_effect": "negative",
              "horizon": "short", "explanation": "Higher crude raises fuel costs.", "uncertainty": "Hedging may offset."},
             {"id": "p2", "node_ids": ["ev_oil", "crude", "banks"], "edge_ids": ["e_event", "e2"], "strength": 0.3, "terminal_effect": "mixed",
              "horizon": "medium", "explanation": "Rates may rise.", "uncertainty": "Indirect."}]
    return {"mode": "live", "event": {"entity": "Crude Oil", "direction": "increase", "change": "+12%", "change_pct": 12.0, "is_simulated": True},
            "nodes": nodes, "edges": edges, "paths": paths,
            "sectors": [{"sector": "Aviation", "exposure": "Possible pressure", "reason": "Fuel costs.", "confidence": "medium"}],
            "warnings": ["1 model-inferred link(s) added."], "meta": {"entity_link": {"node": "crude"}}}


def _llm(monkeypatch, reply, seen=None):
    def fake(prompt, schema_hint=None, use_cache=True):
        if seen is not None:
            seen.append((prompt, use_cache))
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(llm_client, "complete_json", fake)


def test_context_is_compact_and_carries_ids_and_evidence():
    ctx = analyst.build_context(_analysis(), {"available": False, "reason": "nope"})
    assert [p["id"] for p in ctx["paths"]] == ["p1", "p2"]                       # strongest first
    assert ctx["paths"][0]["route"] == ["Oil +12%", "Crude Oil Prices", "Airline Profit Margins"]
    link = next(l for l in ctx["links"] if l["id"] == "e1")
    assert link["evidence_type"] == "llm_inferred" and link["verification"] == "unverified"
    assert next(l for l in ctx["links"] if l["id"] == "e2")["stats"] == {"beta": 0.12, "t_stat": 2.4, "n": 800}
    assert ctx["backtest"] == {"available": False, "reason": "nope"} and len(str(ctx)) < 6000


def test_llm_answer_is_used_and_invalid_citations_are_dropped(monkeypatch):
    seen = []
    _llm(monkeypatch, {"answer": "Airlines face pressure via fuel costs (path p1).", "cited_path_ids": ["p1", "p99"],
                       "cited_node_ids": ["airmargin", "made_up"], "follow_ups": ["a", "b", "c", "d"]}, seen)
    out = analyst.answer_question("Why airlines?", _analysis())
    assert out["mode"] == "llm" and out["cited_path_ids"] == ["p1"] and out["cited_node_ids"] == ["airmargin"]
    assert len(out["follow_ups"]) == 3 and any("removed" in n for n in out["notes"])
    assert "not a probability" in out["disclaimer"] and seen[0][1] is False       # chat prompts are never cached on disk


def test_numbers_not_in_the_analysis_are_flagged(monkeypatch):
    _llm(monkeypatch, {"answer": "Strength 0.7 on p1, but there is an 85% chance of a 40% fall.", "cited_path_ids": ["p1"]})
    out = analyst.answer_question("odds?", _analysis())
    assert any("85" in n and "40" in n for n in out["notes"])
    _llm(monkeypatch, {"answer": "The move is +12% and path p1 has strength 0.7.", "cited_path_ids": ["p1"]})
    assert analyst.answer_question("size?", _analysis())["notes"] == []


@pytest.mark.parametrize("err", [llm_client.LLMUnavailable("no key"), RuntimeError("boom")])
def test_template_fallback_never_raises(monkeypatch, err):
    _llm(monkeypatch, err)
    out = analyst.answer_question("Which sectors are hurt most?", _analysis())
    assert out["mode"] == "template" and "Aviation" in out["answer"] and out["follow_ups"] == []
    out = analyst.answer_question("What is the weakest link?", _analysis())
    assert "Crude Oil Prices → Banks" in out["answer"] and set(out["cited_node_ids"]) <= {"crude", "banks"}
    out = analyst.answer_question("anything", _analysis())
    assert out["cited_path_ids"] == ["p1", "p2"]


def test_template_answers_history_from_the_backtest(monkeypatch):
    _llm(monkeypatch, llm_client.LLMUnavailable("x"))
    bt = {"available": True, "date_range": {"start": "2017-03-13", "end": "2026-10-09"}, "caveat": "Historical co-movement of proxy tickers.",
          "targets": [{"node_id": "airmargin", "label": "Airlines", "n": 12, "hit_rate": {"5": 0.75}, "last_episodes": [{"date": "2026-06-10"}]}]}
    out = analyst.answer_question("Has this happened before?", _analysis(), backtest=bt)
    assert "2026-06-10" in out["answer"] and "9 of 12" in out["answer"] and out["cited_node_ids"] == ["airmargin"]
    out = analyst.answer_question("Has this happened before?", _analysis(), backtest={"available": False, "reason": "no ticker"})
    assert "no ticker" in out["answer"]


def test_hindi_is_detected_and_requested(monkeypatch):
    seen = []
    _llm(monkeypatch, {"answer": "ठीक है", "cited_path_ids": []}, seen)
    out = analyst.answer_question("एयरलाइन पर क्या असर होगा?", _analysis())
    assert out["language"] == "hi" and "Hindi" in seen[0][0]
    _llm(monkeypatch, llm_client.LLMUnavailable("x"))
    assert "घटना" in analyst.answer_question("sector kaun se?", _analysis(), language="hi")["answer"]


def test_history_is_limited_to_last_8_turns(monkeypatch):
    seen = []
    _llm(monkeypatch, {"answer": "ok"}, seen)
    hist = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turn-{i}"} for i in range(12)]
    analyst.answer_question("next", _analysis(), history=hist)
    assert "turn-3" not in seen[0][0] and "turn-4" in seen[0][0] and "turn-11" in seen[0][0]


def test_endpoint_with_analysis_object_and_with_saved_id(monkeypatch):
    _llm(monkeypatch, {"answer": "Via p1.", "cited_path_ids": ["p1"], "cited_node_ids": ["crude"]})
    r = client.post("/api/chat", json={"message": "why?", "analysis": _analysis()})
    assert r.status_code == 200 and r.json()["cited_path_ids"] == ["p1"]
    from app.graph import store
    aid = store.save_analysis(_analysis())
    r = client.post("/api/chat", json={"message": "why?", "analysis_id": aid, "history": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200 and r.json()["mode"] == "llm"
    assert client.post("/api/chat", json={"message": "why?"}).status_code == 422
    assert client.post("/api/chat", json={"message": "why?", "analysis_id": "0" * 24}).status_code == 422   # unknown id, no fallback object


def test_endpoint_template_when_llm_is_down(monkeypatch):
    _llm(monkeypatch, llm_client.LLMUnavailable("down"))
    r = client.post("/api/chat", json={"message": "summary", "analysis": _analysis()})
    assert r.status_code == 200 and r.json()["mode"] == "template"
