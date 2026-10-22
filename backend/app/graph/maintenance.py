"""Keeping the hierarchy and graph consistent as it grows. OWNER: M3

- validate_hierarchy: every node has a sector that exists in the tree; no empty/unknown parents.
- attach_new_node:    put a new node (e.g. proposed by the LLM expander) under the right sector,
                      reusing an existing node when an alias/label already matches (no duplicates).
- find_duplicates:    report nodes whose normalised labels collide.
"""
import re
import networkx as nx
from app.graph.hierarchy import load_tree

_NORM = re.compile(r"[^a-z0-9]+")


def _key(text: str) -> str:
    return _NORM.sub("", (text or "").lower())


def validate_hierarchy(G: nx.DiGraph, tree: dict | None = None) -> list[str]:
    """Return a list of human-readable problems (empty list = healthy)."""
    tree = tree or load_tree()
    problems: list[str] = []
    for nid, a in G.nodes(data=True):
        if a.get("type") == "event":
            continue
        sector = a.get("sector")
        if not sector:
            problems.append(f"node '{nid}' has no sector")
        elif sector not in tree["sector_to_group"]:
            problems.append(f"node '{nid}' has sector '{sector}' which is not in hierarchy.json")
    used = {a.get("sector") for _, a in G.nodes(data=True)}
    for sector in tree["sector_to_group"]:
        if sector not in used:
            problems.append(f"sector '{sector}' in hierarchy.json has no nodes")
    return problems


def find_duplicates(G: nx.DiGraph) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    dups = []
    for nid, a in G.nodes(data=True):
        k = _key(a.get("label", nid))
        if k in seen:
            dups.append((seen[k], nid))
        else:
            seen[k] = nid
    return dups


def attach_new_node(G: nx.DiGraph, node_id: str, label: str, node_type: str,
                    sector: str, polarity: int = 0, tree: dict | None = None) -> tuple[str, bool]:
    """Add a node under `sector`. Returns (id_used, created).

    If a node with the same normalised label or id already exists, that node is reused
    (created=False) so the graph never holds two copies of one concept.
    Unknown sectors raise ValueError: extend data/hierarchy.json first (keeps the tree curated).
    """
    tree = tree or load_tree()
    if sector not in tree["sector_to_group"]:
        raise ValueError(f"unknown sector '{sector}': add it to data/hierarchy.json first")
    for nid, a in G.nodes(data=True):
        if nid == node_id or _key(a.get("label", "")) == _key(label):
            return nid, False
    G.add_node(node_id, label=label, type=node_type, sector=sector, polarity=polarity)
    return node_id, True
