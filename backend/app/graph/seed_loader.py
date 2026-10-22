"""Load data/seed_nodes.json + seed_edges.json into a NetworkX DiGraph. OWNER: M3

Edge attributes stored on the graph (plain python, same names as schemas.Edge):
id, relationship, sign, weight, evidence_type, verification_status, horizon,
explanation, assumptions, evidence, stats
"""
import json
import networkx as nx
from app.config import DATA_DIR


def _read(name: str) -> list[dict]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load_seed_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    for n in _read("seed_nodes.json"):
        attrs = {k: v for k, v in n.items() if k != "id"}
        G.add_node(n["id"], **attrs)

    for e in _read("seed_edges.json"):
        if e["source"] not in G or e["target"] not in G:
            raise ValueError(f"seed edge {e.get('id')} references an unknown node")
        evidence_type = e.get("evidence_type", "domain_rule")
        G.add_edge(
            e["source"], e["target"],
            id=e["id"],
            relationship=e.get("relationship", "influences"),
            sign=e.get("sign", 1),
            weight=e["weight"],
            evidence_type=evidence_type,
            # hand-reviewed domain rules start as 'reviewed'; anything else must earn its status
            verification_status=e.get("verification_status",
                                      "reviewed" if evidence_type == "domain_rule" else "unverified"),
            horizon=e.get("horizon", "short"),
            explanation=e.get("explanation", ""),
            assumptions=list(e.get("assumptions", [])),
            evidence=list(e.get("evidence", [])),
            stats=None,
        )
    return G