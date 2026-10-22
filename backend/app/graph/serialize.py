"""NetworkX graph + paths -> API nodes/edges (only those on kept paths, <=25 nodes). OWNER: M3"""
import networkx as nx
from app.schemas import Node, Edge, ImpactPath
from app.impact.scoring import adverse_when_up, flip_effect


def _effect(signs: set[int]) -> str:
    if not signs or 0 in signs or (1 in signs and -1 in signs):
        return "mixed"
    return "positive" if 1 in signs else "negative"


def graph_to_nodes_edges(G: nx.DiGraph, paths: list[ImpactPath]) -> tuple[list[Node], list[Edge]]:
    node_order: list[str] = []
    edge_order: list[tuple[str, str]] = []
    cumulative: dict[str, set[int]] = {}          # node -> signs of the cumulative effect per path

    for p in paths:
        running = 1
        for i, nid in enumerate(p.node_ids):
            if nid not in node_order:
                node_order.append(nid)
            if i == 0:
                continue
            u = p.node_ids[i - 1]
            data = G[u][nid]
            running *= data["sign"] if data["sign"] != 0 else 0
            cumulative.setdefault(nid, set()).add(running)
            if (u, nid) not in edge_order:
                edge_order.append((u, nid))

    event_node = G.graph.get("event_node")
    nodes = []
    for nid in node_order:
        a = G.nodes[nid]
        if nid == event_node:
            effect = "neutral"
        else:
            effect = _effect(cumulative.get(nid, set()))
            if adverse_when_up(a):                         # colour = good/bad, not up/down
                effect = flip_effect(effect)
        nodes.append(Node(id=nid, label=a["label"], type=a["type"], sector=a.get("sector"), effect=effect))

    edges = []
    for u, v in edge_order:
        d = G[u][v]
        edges.append(Edge(
            id=d["id"], source=u, target=v, relationship=d["relationship"], sign=d["sign"],
            weight=d["weight"], evidence_type=d["evidence_type"],
            verification_status=d["verification_status"], horizon=d["horizon"],
            explanation=d.get("explanation", ""), assumptions=d.get("assumptions", []),
            evidence=d.get("evidence", []), stats=d.get("stats"),
        ))
    return nodes, edges