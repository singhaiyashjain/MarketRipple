"""M2 tests for graph/expander.py and explain/explainer.py - no network needed."""
import networkx as nx

from app.explain.explainer import explain_paths
from app.extraction import llm_client
from app.graph.expander import INFERRED_WEIGHT, propose_edges
from app.schemas import ExtractedEvent, ImpactPath


def _graph():
    G = nx.DiGraph()
    for n, label in [("crude", "Crude Oil Prices"), ("avfuel", "Aviation Fuel Costs"),
                     ("airop", "Airline Operating Costs"), ("inflation", "Inflationary Pressure")]:
        G.add_node(n, label=label)
    G.add_edge("crude", "avfuel", id="s1", explanation="Jet fuel tracks crude.", weight=0.9,
               evidence_type="domain_rule", assumptions=["Refining margins stable"])
    G.add_edge("avfuel", "airop", id="s2", explanation="Fuel is a major airline cost.", weight=0.8,
               evidence_type="domain_rule", assumptions=["Limited hedging"])
    return G


EVENT = ExtractedEvent(event_type="commodity_price_shock", entity="Crude Oil Prices", direction="increase")


def test_expander_filters_and_tags(monkeypatch):
    reply = {"edges": [
        {"source": "crude", "target": "inflation", "relationship": "influences", "sign": 1,
         "horizon": "short", "explanation": "Fuel feeds into CPI.", "assumptions": ["Pass-through"]},
        {"source": "crude", "target": "avfuel", "sign": 1, "explanation": "duplicate of seed"},
        {"source": "crude", "target": "ghost_node", "sign": 1, "explanation": "unknown endpoint"},
        {"source": "crude", "target": "crude", "sign": 1, "explanation": "self loop"},
        {"source": "Inflationary Pressure", "target": "Airline Operating Costs", "sign": 5,
         "explanation": "bad sign"},
        {"source": "inflation", "target": "airop", "sign": 1, "explanation": ""},
    ]}
    monkeypatch.setattr(llm_client, "complete_json", lambda p, schema_hint=None: reply)
    edges = propose_edges(EVENT, _graph(), k=8)
    assert [e.id for e in edges] == ["x_crude_inflation"]
    e = edges[0]
    assert e.evidence_type == "llm_inferred" and e.verification_status == "unverified"
    assert e.weight == INFERRED_WEIGHT


def test_expander_returns_empty_when_llm_down(monkeypatch):
    def boom(p, schema_hint=None):
        raise llm_client.LLMUnavailable("down")
    monkeypatch.setattr(llm_client, "complete_json", boom)
    assert propose_edges(EVENT, _graph()) == []


def test_explainer_fills_explanation_and_uncertainty():
    G = _graph()
    p = ImpactPath(id="p1", node_ids=["crude", "avfuel", "airop"], edge_ids=["s1", "s2"],
                   strength=0.72, terminal_effect="negative", horizon="short")
    out = explain_paths(G, [p])[0]
    assert "Crude Oil Prices → Aviation Fuel Costs → Airline Operating Costs" in out.explanation
    assert "Jet fuel tracks crude." in out.explanation
    assert "Limited hedging" in out.uncertainty and "not a probability" in out.uncertainty
    assert p.explanation == ""            # input not mutated


def test_explainer_flags_inferred_links():
    G = _graph()
    G.add_edge("airop", "inflation", id="x1", explanation="Costs pass into prices.", weight=0.3,
               evidence_type="llm_inferred", assumptions=[])
    p = ImpactPath(id="p2", node_ids=["avfuel", "airop", "inflation"], edge_ids=["s2", "x1"],
                   strength=0.24, terminal_effect="mixed", horizon="medium")
    out = explain_paths(G, [p])[0]
    assert "model-suggested" in out.explanation
    assert "model-inferred" in out.uncertainty and "conditional or weak" in out.uncertainty
