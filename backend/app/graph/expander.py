"""LLM proposes extra edges missing from seed graph. OWNER: M2
Every proposed edge MUST be tagged evidence_type='llm_inferred', verification_status='unverified'.

Safety rules enforced here (not left to the prompt):
- endpoints must already exist in G (no invented nodes -> no orphan/hallucinated entities)
- no self-loops, no duplicates of existing edges
- weight is NOT taken from the model: fixed at the rubric's "weak / indirect" level (0.3)
- any LLM/network failure -> returns [] (expansion is optional; the seed graph still works)
"""
import json

import networkx as nx

from app.extraction import llm_client
from app.extraction.prompts import EXPAND_PROMPT
from app.schemas import Edge, Evidence, ExtractedEvent

INFERRED_WEIGHT = 0.3  # data/README.md rubric: 0.3 = weak / indirect
_RELATIONSHIPS = {"influences", "may_pressure", "may_benefit", "may_influence"}
_HORIZONS = {"immediate", "short", "medium", "long"}


def _resolve(value, G: nx.DiGraph, by_label: dict[str, str]):
    """Accept a node id or an exact (case-insensitive) label; return the node id or None."""
    if value in G:
        return value
    return by_label.get(str(value).strip().lower())


def propose_edges(event: ExtractedEvent, G: nx.DiGraph, k: int = 8) -> list[Edge]:
    nodes = [{"id": n, "label": d.get("label", n)} for n, d in G.nodes(data=True)]
    by_label = {str(x["label"]).lower(): x["id"] for x in nodes}
    prompt = EXPAND_PROMPT.format(k=k, event=event.model_dump_json(),
                                  nodes=json.dumps(nodes, ensure_ascii=False))
    try:
        data = llm_client.complete_json(prompt)
    except Exception:
        return []

    items = data.get("edges", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []

    out: list[Edge] = []
    seen: set[tuple[str, str]] = set()
    for it in items:
        if len(out) >= k:
            break
        if not isinstance(it, dict):
            continue
        src = _resolve(it.get("source"), G, by_label)
        dst = _resolve(it.get("target"), G, by_label)
        if not src or not dst or src == dst or G.has_edge(src, dst) or (src, dst) in seen:
            continue
        sign = it.get("sign")
        if sign not in (-1, 0, 1):
            continue
        rel = it.get("relationship") if it.get("relationship") in _RELATIONSHIPS else "may_influence"
        horizon = it.get("horizon") if it.get("horizon") in _HORIZONS else "medium"
        explanation = str(it.get("explanation") or "").strip()[:300]
        if not explanation:
            continue  # an unexplained edge is useless in an "explainable" product
        assumptions = [str(a)[:120] for a in (it.get("assumptions") or []) if a][:3]
        seen.add((src, dst))
        out.append(Edge(
            id=f"x_{src}_{dst}", source=src, target=dst, relationship=rel, sign=sign,
            weight=INFERRED_WEIGHT, evidence_type="llm_inferred", verification_status="unverified",
            horizon=horizon, explanation=explanation, assumptions=assumptions,
            evidence=[Evidence(source_type="llm",
                               text="Suggested by the language model; not verified against a source.")],
        ))
    return out
