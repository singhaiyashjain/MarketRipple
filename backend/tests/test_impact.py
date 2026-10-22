import networkx as nx
from app.schemas import ExtractedEvent
from app.graph.builder import build_graph
from app.graph.seed_loader import load_seed_graph
from app.impact.engine import find_paths
from app.impact.sectors import summarize_sectors
from app.graph.serialize import graph_to_nodes_edges
from app.config import settings


def _oil(direction="increase"):
    return ExtractedEvent(event_type="commodity_price_shock", entity="Crude Oil",
                          indicator="crude_oil_price", direction=direction, change="+12%")


def test_seed_graph_loads():
    G = load_seed_graph()
    assert G.number_of_nodes() >= 25 and G.number_of_edges() >= 26
    assert all(0 <= d["weight"] <= 1 for _, _, d in G.edges(data=True))


def test_oil_to_airline_path():
    G = build_graph(_oil(), use_llm=False)
    p = next(p for p in find_paths(G, _oil()) if p.node_ids[-1] == "indigo")
    assert p.node_ids == ["ev_crude", "crude", "avfuel", "airop", "airmargin", "indigo"]
    assert p.terminal_effect == "negative" and 0.3 < p.strength < 0.4


def test_paths_are_bounded_acyclic_and_sorted():
    G = build_graph(_oil(), use_llm=False)
    paths = find_paths(G, _oil())
    assert paths and len(paths) <= settings.top_k_paths
    for p in paths:
        assert len(set(p.node_ids)) == len(p.node_ids)               # no cycles
        assert len(p.edge_ids) <= settings.max_path_len + 1
    assert [p.strength for p in paths] == sorted((p.strength for p in paths), reverse=True)
    nodes, edges = graph_to_nodes_edges(G, paths)
    assert len(nodes) <= settings.max_nodes
    ids = {n.id for n in nodes}
    assert all(e.source in ids and e.target in ids for e in edges)


def test_falling_oil_flips_airline_effect():
    ev = _oil("decrease")
    G = build_graph(ev, use_llm=False)
    p = next(p for p in find_paths(G, ev) if p.node_ids[-1] == "indigo")
    assert p.terminal_effect == "positive"


def test_rate_hike_reaches_real_estate_and_banks():
    ev = ExtractedEvent(event_type="interest_rate_hike", entity="Reserve Bank of India",
                        indicator="policy_interest_rate", direction="increase")
    G = build_graph(ev, use_llm=False)
    ends = {p.node_ids[-1] for p in find_paths(G, ev)}
    assert {"realestate", "banks"} <= ends


def test_rupee_depreciation_maps_to_usdinr_up():
    ev = ExtractedEvent(event_type="currency_depreciation", entity="Rupee", indicator=None, direction="decrease")
    G = build_graph(ev, use_llm=False)
    assert G.graph["event_node"] == "ev_usdinr" and G["ev_usdinr"]["usdinr"]["sign"] == 1
    sectors = {s.sector for s in summarize_sectors(G, find_paths(G, ev))}
    assert {"IT", "Pharma"} <= sectors


def test_unknown_event_gives_no_paths_and_warning():
    ev = ExtractedEvent(event_type="celebrity_wedding", entity="Somebody", direction="increase")
    G = build_graph(ev, use_llm=False)
    assert find_paths(G, ev) == [] and G.graph["warnings"]


def test_sector_confidence_rubric():
    G = build_graph(_oil(), use_llm=False)
    sec = {s.sector: s for s in summarize_sectors(G, find_paths(G, _oil()))}
    assert sec["Aviation"].exposure == "Possible pressure" and sec["Aviation"].confidence == "medium"
    assert sec["Oil & Gas - ONGC"].exposure == "Potential benefit"     # winners and losers inside one
    assert sec["Oil & Gas - BPCL"].exposure == "Possible pressure"     # sector are shown separately
    assert sec["Banks"].exposure == "Indirect / uncertain"


def test_cost_nodes_are_adverse_when_they_rise():
    G = build_graph(_oil(), use_llm=False)
    paths = {p.node_ids[-1]: p for p in find_paths(G, _oil())}
    assert paths["asianpaint"].terminal_effect == "negative"           # input costs up = pressure
    assert paths["bpcl"].terminal_effect == "negative"
    assert paths["ongc"].terminal_effect == "positive"                 # producer revenue up = benefit
    nodes, _ = graph_to_nodes_edges(G, list(paths.values()))
    eff = {n.id: n.effect for n in nodes}
    assert eff["avfuel"] == "negative" and eff["crude"] == "positive" and eff["ev_crude"] == "neutral"


def test_nlp_links_what_keywords_miss():
    ev = ExtractedEvent(event_type="fuel_price_hike", entity="Diesel prices", direction="increase")
    G = build_graph(ev, use_llm=False)
    assert G.graph["link"]["node"] == "diesel"                         # exact or NLP, never lost
    assert find_paths(G, ev)


def test_nlp_synonyms_and_unknowns():
    from app.graph.linker import NodeLinker, infer_direction
    L = NodeLinker(load_seed_graph())
    assert L.link("jet fuel")[0] == "avfuel"
    assert L.link("foreign institutional investors")[0] == "fii_flows"
    assert L.link("celebrity wedding")[0] is None
    assert infer_direction("Brent surges 5%") == "increase" and infer_direction("rupee slumps") == "decrease"
    assert infer_direction("-3%") == "decrease" and infer_direction("nothing here") is None


def test_direction_filled_by_nlp_when_missing():
    ev = ExtractedEvent(event_type="commodity_price_shock", entity="Crude Oil", indicator="crude_oil_price",
                        direction=None, change="-8%")
    G = build_graph(ev, use_llm=False)
    assert ev.direction == "decrease" and G["ev_crude"]["crude"]["sign"] == -1