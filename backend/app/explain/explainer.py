"""Human-readable explanations per path/edge. OWNER: M2
Template-based (deterministic, works offline): chain of labels + one reason per hop taken from
edge.explanation, and an uncertainty note built from edge assumptions / evidence types / weights.
"""
import networkx as nx

from app.schemas import ImpactPath

CONDITIONAL_WEIGHT = 0.5   # data/README.md rubric: <= 0.5 = moderate/conditional or weaker


def _label(G: nx.DiGraph, node_id: str) -> str:
    return G.nodes[node_id].get("label", node_id) if node_id in G else node_id


def _explain_one(G: nx.DiGraph, path: ImpactPath) -> tuple[str, str]:
    ids = path.node_ids
    labels = [_label(G, n) for n in ids]
    steps: list[str] = []
    assumptions: list[str] = []
    n_inferred = 0
    n_weak = 0

    for i, (u, v) in enumerate(zip(ids, ids[1:]), start=1):
        e = G.get_edge_data(u, v) or {}
        why = (e.get("explanation") or "").strip() or "Relationship recorded without a written explanation."
        tag = ""
        if e.get("evidence_type") == "llm_inferred":
            n_inferred += 1
            tag = " (model-suggested, unverified)"
        if float(e.get("weight", 1.0)) <= CONDITIONAL_WEIGHT:
            n_weak += 1
        steps.append(f"{i}. {labels[i-1]} → {labels[i]}{tag}: {why}")
        for a in e.get("assumptions", []) or []:
            if a not in assumptions:
                assumptions.append(a)

    explanation = " → ".join(labels) + ".\n" + "\n".join(steps)

    notes: list[str] = []
    if assumptions:
        notes.append("Depends on: " + "; ".join(assumptions) + ".")
    if n_inferred:
        notes.append(f"{n_inferred} link(s) are model-inferred and not yet verified.")
    if n_weak:
        notes.append(f"{n_weak} link(s) are conditional or weak.")
    notes.append("Plausible transmission channel; path strength is a relative score, not a probability.")
    return explanation, " ".join(notes)


def explain_paths(G: nx.DiGraph, paths: list[ImpactPath]) -> list[ImpactPath]:
    result = []
    for p in paths:
        explanation, uncertainty = _explain_one(G, p)
        result.append(p.model_copy(update={"explanation": explanation, "uncertainty": uncertainty}))
    return result
