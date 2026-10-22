"""Hierarchy over the graph: Economy (L0) > group (L1) > sector (L2) > node (L3). OWNER: M3

Pure python (no pydantic) so it is easy to test. The tree lives in data/hierarchy.json.
roll_up() answers: "which groups/sectors are hit, and how strongly, on the kept paths?"
"""
import json
from functools import lru_cache
import networkx as nx
from app.config import DATA_DIR

EFFECT_RANK = {"negative": -1, "positive": 1, "mixed": 0, "neutral": 0, "unknown": 0}


@lru_cache(maxsize=1)
def load_tree(path=None) -> dict:
    raw = json.loads((path or DATA_DIR / "hierarchy.json").read_text(encoding="utf-8"))
    sector_to_group = {s: g for g, sectors in raw["groups"].items() for s in sectors}
    return {"root": raw["root"], "groups": raw["groups"], "sector_to_group": sector_to_group}


def ancestors(sector: str | None, tree: dict | None = None) -> list[str]:
    """['Indian Economy & Markets', group, sector] for a known sector, else just [root]."""
    tree = tree or load_tree()
    if not sector or sector not in tree["sector_to_group"]:
        return [tree["root"]]
    return [tree["root"], tree["sector_to_group"][sector], sector]


def level_of(node_id: str, G: nx.DiGraph) -> int:
    """Depth in the hierarchy: event=0 (outside tree), sector-level nodes=2, leaf nodes=3."""
    a = G.nodes[node_id]
    if a.get("type") == "event":
        return 0
    return 2 if a.get("type") == "sector" else 3


def roll_up(G: nx.DiGraph, paths: list, tree: dict | None = None) -> list[dict]:
    """Aggregate path terminals up the tree.

    paths: objects with .node_ids, .strength, .terminal_effect (ImpactPath or any duck type).
    Returns [{group, strength, effect, sectors:[{sector, strength, effect, nodes:[labels]}]}]
    sorted by strength. A group/sector with opposing path effects is reported 'mixed'.
    strength = max path strength reaching it (relative score, not a probability).
    """
    tree = tree or load_tree()
    groups: dict[str, dict] = {}
    for p in paths:
        end = p.node_ids[-1]
        sector = G.nodes[end].get("sector")
        if sector in (None, "Macro"):
            continue
        group = tree["sector_to_group"].get(sector)
        if group is None:
            continue
        g = groups.setdefault(group, {"group": group, "strength": 0.0, "_eff": set(), "_sec": {}})
        s = g["_sec"].setdefault(sector, {"sector": sector, "strength": 0.0, "_eff": set(), "nodes": []})
        for bucket in (g, s):
            bucket["strength"] = max(bucket["strength"], p.strength)
            bucket["_eff"].add(p.terminal_effect)
        label = G.nodes[end]["label"]
        if label not in s["nodes"]:
            s["nodes"].append(label)

    def eff(effects: set) -> str:
        ranks = {EFFECT_RANK.get(e, 0) for e in effects}
        if ranks == {-1}:
            return "negative"
        if ranks == {1}:
            return "positive"
        return "mixed"

    out = []
    for g in groups.values():
        sectors = sorted(g["_sec"].values(), key=lambda s: -s["strength"])
        for s in sectors:
            s["effect"] = eff(s.pop("_eff"))
            s["strength"] = round(s["strength"], 3)
        out.append({"group": g["group"], "strength": round(g["strength"], 3),
                    "effect": eff(g["_eff"]), "sectors": sectors})
    out.sort(key=lambda g: -g["strength"])
    return out
