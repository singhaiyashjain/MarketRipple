"""Graph algorithms over the impact graph. OWNER: M3  (mentor requirement: graph algorithms)

Pure NetworkX (no pydantic). Three algorithms, each answering a different question:

1. BFS impact order   - "how many hops from the event?"  1st-order = direct, 2nd = knock-on ...
2. Dijkstra best path - "what is the single strongest chain to each sector/asset?"
                        cost = -log(weight), so the shortest path IS the max product of weights
                        (same score as path_strength) and it is safe on the known cycle.
3. Centrality         - "which intermediate variables carry the most impact?"
                        weighted betweenness on the reachable subgraph + PageRank.
All scores are relative, never probabilities.
"""
import math
import networkx as nx

TERMINAL_TYPES = {"sector", "index", "company"}
ORDER_NAMES = {1: "Event link", 2: "Direct impact", 3: "Second-order", 4: "Third-order"}


def _cost(u, v, data) -> float:
    return -math.log(max(data.get("weight", 0.01), 1e-6))


def bfs_orders(G: nx.DiGraph, src: str, nodes: set[str] | None = None) -> dict[str, int]:
    """Hop distance from the event. If `nodes` is given, restrict the search to those nodes
    (use the visible path nodes so numbers match what the user sees)."""
    H = G.subgraph(nodes | {src}) if nodes else G
    return dict(nx.single_source_shortest_path_length(H, src))


def layers(orders: dict[str, int], G: nx.DiGraph) -> list[dict]:
    """Group node ids by hop count -> [{order, name, nodes:[{id,label}]}]."""
    by: dict[int, list[str]] = {}
    for nid, d in orders.items():
        by.setdefault(d, []).append(nid)
    out = []
    for d in sorted(by):
        if d == 0:
            continue
        out.append({"order": d, "name": ORDER_NAMES.get(d, f"{d - 1}th-order"),
                    "nodes": [{"id": n, "label": G.nodes[n]["label"]} for n in sorted(by[d])]})
    return out


def best_paths(G: nx.DiGraph, src: str) -> list[dict]:
    """Strongest chain to every terminal (sector/index/company) reachable from src."""
    dist, paths = nx.single_source_dijkstra(G, src, weight=_cost)
    out = []
    for tgt, p in paths.items():
        if tgt == src or len(p) < 3 or G.nodes[tgt].get("type") not in TERMINAL_TYPES:
            continue
        out.append({"target": tgt, "label": G.nodes[tgt]["label"], "node_ids": p,
                    "strength": round(math.exp(-dist[tgt]), 3)})
    out.sort(key=lambda x: -x["strength"])
    return out


def influence(G: nx.DiGraph, src: str, top: int = 5) -> list[dict]:
    """Rank transmission nodes (not the event, not final sectors/companies).

    score = 0.5*betweenness + 0.5*pagerank, each min-max scaled on the reachable subgraph.
    """
    reach = nx.descendants(G, src) | {src}
    H = G.subgraph(reach).copy()
    if H.number_of_nodes() < 3:
        return []
    bet = nx.betweenness_centrality(H, weight=_cost, normalized=True)
    pr = nx.pagerank(H, weight="weight")

    def scale(d):
        lo, hi = min(d.values()), max(d.values())
        return {k: (v - lo) / (hi - lo) if hi > lo else 0.0 for k, v in d.items()}

    b, p = scale(bet), scale(pr)
    rows = []
    for n in H:
        if n == src or H.nodes[n].get("type") in TERMINAL_TYPES:
            continue
        rows.append({"id": n, "label": H.nodes[n]["label"], "sector": H.nodes[n].get("sector"),
                     "score": round(0.5 * b[n] + 0.5 * p[n], 3),
                     "betweenness": round(bet[n], 3), "pagerank": round(pr[n], 3)})
    rows.sort(key=lambda r: -r["score"])
    return rows[:top]


def analyse(G: nx.DiGraph, src: str, visible: set[str]) -> dict:
    """Everything the UI needs, JSON-serialisable."""
    orders = bfs_orders(G, src, visible)
    return {
        "orders": orders,
        "layers": layers(orders, G),
        "best_paths": best_paths(G, src)[:5],
        "influence": influence(G, src),
    }
