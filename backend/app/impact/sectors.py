"""Group paths' terminal nodes into sector exposure table. OWNER: M3

Confidence rubric (defined, not hand-typed):
  high   : strength >= 0.5, no llm_inferred edge, and >= 1 edge is quant_verified
  medium : no llm_inferred edge and strength >= 0.15
  low    : otherwise (weak or model-inferred chain)
If one sector has paths with opposite effects (e.g. Oil & Gas: producers gain, OMCs lose) it is split
into one row per terminal node instead of being averaged away.
Exposure wording: negative -> 'Possible pressure', positive -> 'Potential benefit',
mixed -> 'Indirect / uncertain'. Chains with >= 5 economic hops are always labelled indirect.
"""
import networkx as nx
from app.schemas import ImpactPath, SectorExposure

SKIP_SECTORS = {"Macro", None}                 # intermediate macro variables are not 'sectors'
WORDING = {"negative": "Possible pressure", "positive": "Potential benefit", "mixed": "Indirect / uncertain"}
CONF_ORDER = ["low", "medium", "high"]


def path_confidence(G: nx.DiGraph, p: ImpactPath) -> str:
    edges = [G[u][v] for u, v in zip(p.node_ids, p.node_ids[1:])]
    types = {e["evidence_type"] for e in edges}
    if "llm_inferred" in types:
        return "low"
    if p.strength >= 0.5 and "quant_verified" in types:
        return "high"
    return "medium" if p.strength >= 0.15 else "low"


def _row(G: nx.DiGraph, name: str, ps: list[ImpactPath], conflicting: bool = False) -> SectorExposure:
    best = max(ps, key=lambda p: p.strength)
    effect = "mixed" if conflicting else best.terminal_effect
    if len(best.edge_ids) - 1 >= 5:                        # long chain => indirect, whatever the sign
        effect = "mixed"
    last_edge = G[best.node_ids[-2]][best.node_ids[-1]]
    return SectorExposure(sector=name, exposure=WORDING[effect],
                          reason=last_edge.get("explanation", ""), confidence=path_confidence(G, best))


def summarize_sectors(G: nx.DiGraph, paths: list[ImpactPath]) -> list[SectorExposure]:
    by_sector: dict[str, list[ImpactPath]] = {}
    for p in paths:
        sector = G.nodes[p.node_ids[-1]].get("sector")
        if sector in SKIP_SECTORS:
            continue
        by_sector.setdefault(sector, []).append(p)

    out: list[SectorExposure] = []
    for sector, ps in by_sector.items():
        if len({p.terminal_effect for p in ps}) == 1:
            out.append(_row(G, sector, ps))
        else:                                              # winners and losers inside one sector: show both
            by_terminal: dict[str, list[ImpactPath]] = {}
            for p in ps:
                by_terminal.setdefault(p.node_ids[-1], []).append(p)
            if len(by_terminal) == 1:                      # same node reached with opposing signs
                out.append(_row(G, sector, ps, conflicting=True))
                continue
            for tid, tps in by_terminal.items():
                out.append(_row(G, f"{sector} - {G.nodes[tid]['label']}", tps))
    out.sort(key=lambda s: -CONF_ORDER.index(s.confidence))
    return out