"""Bounded, sign-aware path search from event node to affected nodes. OWNER: M3
Respects edge direction; caps length (settings.max_path_len economic hops, the event->seed
link is not counted), top-k and visible-node count; keeps at most 2 paths per terminal node.
"""
import networkx as nx
from app.config import settings
from app.schemas import ExtractedEvent, ImpactPath
from app.impact.scoring import path_strength, terminal_effect, adverse_when_up, flip_effect
from app.impact.horizon import path_horizon

TERMINAL_TYPES = {"sector", "index", "company"}
MIN_STRENGTH = 0.05
MAX_PATHS_PER_TERMINAL = 2


def _terminals(G: nx.DiGraph, src: str) -> set[str]:
    return {n for n in G if n != src
            and (G.out_degree(n) == 0 or G.nodes[n].get("type") in TERMINAL_TYPES)}


def _default_explanation(G: nx.DiGraph, nodes: list[str], edges: list[dict]) -> str:
    chain = " → ".join(G.nodes[n]["label"] for n in nodes)
    reasons = " ".join(e["explanation"] for e in edges[1:] if e.get("explanation"))   # skip event link
    return f"{chain}. {reasons}".strip()


def _default_uncertainty(edges: list[dict]) -> str:
    seen: list[str] = []
    for e in edges:
        for a in e.get("assumptions", []):
            if a not in seen:
                seen.append(a)
    parts = []
    if seen:
        parts.append("Assumes: " + "; ".join(seen) + ".")
    if any(e["evidence_type"] == "llm_inferred" for e in edges):
        parts.append("Includes model-inferred, unverified links.")
    parts.append("Relative path strength, not a probability.")
    return " ".join(parts)


def find_paths(G: nx.DiGraph, event: ExtractedEvent) -> list[ImpactPath]:
    src = G.graph.get("event_node")
    if not src or src not in G:
        return []

    candidates: list[tuple[float, list[str], list[dict]]] = []
    per_terminal: dict[str, list] = {}
    for tgt in _terminals(G, src):
        for nodes in nx.all_simple_paths(G, src, tgt, cutoff=settings.max_path_len + 1):
            if len(nodes) < 3:                               # need >= 1 economic hop
                continue
            edges = [G[u][v] for u, v in zip(nodes, nodes[1:])]
            strength = path_strength([e["weight"] for e in edges])
            if strength >= MIN_STRENGTH:
                per_terminal.setdefault(tgt, []).append((strength, nodes, edges))

    for items in per_terminal.values():
        items.sort(key=lambda t: (-t[0], len(t[1])))
        candidates.extend(items[:MAX_PATHS_PER_TERMINAL])
    candidates.sort(key=lambda t: (-t[0], len(t[1])))

    kept: list[ImpactPath] = []
    visible: set[str] = set()
    for strength, nodes, edges in candidates:
        if len(kept) >= settings.top_k_paths:
            break
        if len(visible | set(nodes)) > settings.max_nodes:   # keep the graph readable
            continue
        visible |= set(nodes)
        effect = terminal_effect([e["sign"] for e in edges])
        if adverse_when_up(G.nodes[nodes[-1]]):               # cost-type terminal: rising = adverse
            effect = flip_effect(effect)
        kept.append(ImpactPath(
            id=f"p{len(kept) + 1}",
            node_ids=nodes,
            edge_ids=[e["id"] for e in edges],
            strength=strength,
            terminal_effect=effect,
            horizon=path_horizon([e["horizon"] for e in edges]),
            explanation=_default_explanation(G, nodes, edges),    # M2's explainer overwrites these
            uncertainty=_default_uncertainty(edges),
        ))
    return kept