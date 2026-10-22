"""Tests for hierarchy + graph algorithms (pure NetworkX). Run: pytest tests/test_graph_analysis.py
or, without pydantic installed:  python tests/run_plain.py"""
import json
from types import SimpleNamespace
import networkx as nx
from app.config import DATA_DIR
from app.graph import hierarchy, maintenance
from app.impact import layers


def seed_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    for n in json.loads((DATA_DIR / "seed_nodes.json").read_text(encoding="utf-8")):
        G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
    for e in json.loads((DATA_DIR / "seed_edges.json").read_text(encoding="utf-8")):
        G.add_edge(e["source"], e["target"], id=e["id"], weight=e["weight"], sign=e["sign"])
    G.add_node("ev", label="Crude +12%", type="event", sector=None)
    G.add_edge("ev", "crude", id="e0", weight=1.0, sign=1)
    return G


def test_every_seed_sector_is_in_tree():
    assert maintenance.validate_hierarchy(seed_graph()) == []


def test_ancestors():
    assert hierarchy.ancestors("Aviation")[1:] == ["Industrials & Transport", "Aviation"]
    assert hierarchy.ancestors("Nope") == [hierarchy.load_tree()["root"]]


def test_bfs_orders_increase_along_edges():
    G = seed_graph()
    o = layers.bfs_orders(G, "ev")
    assert o["ev"] == 0 and o["crude"] == 1 and o["avfuel"] == 2


def test_best_path_matches_product_of_weights():
    G = seed_graph()
    for bp in layers.best_paths(G, "ev"):
        prod = 1.0
        for u, v in zip(bp["node_ids"], bp["node_ids"][1:]):
            prod *= G[u][v]["weight"]
        assert abs(prod - bp["strength"]) < 0.005


def test_influence_excludes_event_and_terminals():
    G = seed_graph()
    rows = layers.influence(G, "ev")
    assert rows and all(r["id"] != "ev" for r in rows)
    assert all(G.nodes[r["id"]]["type"] not in layers.TERMINAL_TYPES for r in rows)


def test_roll_up_groups_and_flags_mixed():
    G = seed_graph()
    mk = lambda ids, s, e: SimpleNamespace(node_ids=ids, strength=s, terminal_effect=e)
    paths = [mk(["ev", "crude", "avfuel", "airop", "airmargin"], 0.5, "negative"),
             mk(["ev", "crude", "upstream", "ongc"], 0.6, "positive")]
    out = {g["group"]: g for g in hierarchy.roll_up(G, paths)}
    assert out["Industrials & Transport"]["effect"] == "negative"
    assert out["Energy & Commodities"]["effect"] == "positive"


def test_attach_new_node_reuses_duplicates_and_rejects_unknown_sector():
    G = seed_graph()
    nid, created = maintenance.attach_new_node(G, "x1", "Crude Oil Prices", "commodity", "Energy")
    assert (nid, created) == ("crude", False)
    nid, created = maintenance.attach_new_node(G, "steel", "Steel Prices", "commodity", "Energy")
    assert created and G.nodes["steel"]["sector"] == "Energy"
    try:
        maintenance.attach_new_node(G, "z", "Z", "indicator", "Unknown Sector")
        assert False
    except ValueError:
        pass


def test_verifier_rules():
    from app.evidence.verifier import verify_data
    base = {"sign": 1, "stats": None}
    assert verify_data({**base, "evidence_type": "llm_inferred", "evidence": []}) == ("llm_inferred", "unverified")
    assert verify_data({**base, "evidence_type": "llm_inferred", "evidence": [{"source_type": "news"}]})[1] == "supported"
    assert verify_data({**base, "evidence_type": "domain_rule", "evidence": [{"source_type": "domain_knowledge"}]})[1] == "reviewed"
    assert verify_data({**base, "evidence_type": "domain_rule", "evidence": []})[1] == "unverified"
    opp = type("S", (), {"beta": -0.5, "t_stat": 3.0})()
    assert verify_data({"sign": 1, "stats": opp, "evidence_type": "domain_rule", "evidence": []})[1] == "conflicting"


def test_attach_evidence_quotes_only_real_sentences():
    from app.evidence.evidence import attach_evidence
    G = seed_graph(); G.graph["event_node"] = "ev"
    for _, _, d in G.edges(data=True):
        d.setdefault("evidence_type", "domain_rule"); d.setdefault("explanation", "x")
        d.setdefault("evidence", []); d.setdefault("verification_status", "reviewed")
    ev = SimpleNamespace(entity="Crude Oil", indicator="crude_oil_price")
    news = "Crude oil prices surge by 12%. Airlines warn that aviation fuel costs will bite."
    attach_evidence(G, ev, news)
    quotes = [e["text"] for e in G["ev"]["crude"]["evidence"] if e["source_type"] == "news"]
    assert quotes == ["Crude oil prices surge by 12%."]
    assert all(e["source_type"] != "news" for e in G["crude"]["inflation"]["evidence"])
