"""Validate data/seed_*.json + hierarchy.json. Run before every commit:  python scripts/validate_seed.py
Checks: unique ids, edges reference real nodes, weights in rubric range, sign in {-1,0,1},
every node's sector exists in hierarchy.json, polarity in {-1,0,1}, known cycles reported."""
import json
import sys
from pathlib import Path

import networkx as nx

DATA = Path(__file__).resolve().parents[1] / "data"
TYPES = {"event", "commodity", "indicator", "sector", "company", "index", "currency", "policy", "country"}
HORIZONS = {"immediate", "short", "medium", "long"}


def main() -> int:
    nodes = json.loads((DATA / "seed_nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((DATA / "seed_edges.json").read_text(encoding="utf-8"))
    tree = json.loads((DATA / "hierarchy.json").read_text(encoding="utf-8"))
    sectors = {s for ss in tree["groups"].values() for s in ss}
    errs: list[str] = []
    warns: list[str] = []
    ids = [n["id"] for n in nodes]
    errs += [f"duplicate node id {i}" for i in {x for x in ids if ids.count(x) > 1}]
    for n in nodes:
        if n["type"] not in TYPES: errs.append(f"{n['id']}: bad type {n['type']}")
        if n.get("polarity") not in (-1, 0, 1): errs.append(f"{n['id']}: polarity must be -1/0/1")
        if n.get("sector") not in sectors: errs.append(f"{n['id']}: sector {n.get('sector')!r} not in hierarchy.json")
    eids = [e["id"] for e in edges]
    errs += [f"duplicate edge id {i}" for i in {x for x in eids if eids.count(x) > 1}]
    idset = set(ids)
    for e in edges:
        for k in ("source", "target"):
            if e[k] not in idset: errs.append(f"{e['id']}: unknown {k} {e[k]}")
        if e["sign"] not in (-1, 0, 1): errs.append(f"{e['id']}: bad sign")
        if not 0 < e["weight"] <= 1: errs.append(f"{e['id']}: weight out of (0,1]")
        if e.get("horizon", "short") not in HORIZONS: errs.append(f"{e['id']}: bad horizon")
        if not e.get("explanation"): errs.append(f"{e['id']}: missing explanation")
        if not e.get("assumptions"): warns.append(f"{e['id']}: no assumptions listed (add one where the link can fail)")
    G = nx.DiGraph((e["source"], e["target"]) for e in edges)
    cycles = list(nx.simple_cycles(G))
    print(f"{len(nodes)} nodes, {len(edges)} edges, {len(cycles)} cycle(s): {[' > '.join(c) for c in cycles]}")
    unused = sectors - {n["sector"] for n in nodes}
    if unused: print("sectors in hierarchy with no nodes:", sorted(unused))
    print(f"{len(warns)} warning(s) (edges without assumptions)") if warns else None
    for e in errs: print("ERROR", e)
    print("OK" if not errs else f"{len(errs)} error(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
