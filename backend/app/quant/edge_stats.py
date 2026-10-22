"""Fill edge.stats from data; upgrade evidence_type to quant_verified when significant & stable.
OWNER: M4. Edges without data keep stats=None (UI shows 'no historical data').

Upgrade rule (all must hold): ticker for both nodes, different tickers, n >= 60 returns,
|t| >= 2, stability != low, and sign(beta) == edge sign (edge sign 0 never upgrades)."""
import logging
import networkx as nx
from app.schemas import ExtractedEvent, EdgeStats
from app.quant import data_loader
from app.quant.betas import estimate_beta

log = logging.getLogger("finpulse.quant")
NOTE = "Historical co-movement of daily returns (proxy tickers), not proof of causation."


def compute_edge_stats(source_node: str, target_node: str) -> EdgeStats | None:
    ts, tt = data_loader.ticker_for(source_node), data_loader.ticker_for(target_node)
    if not ts or not tt or ts == tt:                       # no proxy, or identical series
        return None
    try:
        res = estimate_beta(data_loader.load_prices(ts), data_loader.load_prices(tt))
    except (FileNotFoundError, ValueError) as exc:
        log.info("no stats for %s->%s: %s", source_node, target_node, exc)
        return None
    return EdgeStats(**res, note=NOTE)


def _upgrade(stats: EdgeStats, sign: int) -> bool:
    return (sign != 0 and stats.n is not None and stats.n >= 60 and abs(stats.t_stat or 0) >= 2
            and stats.stability != "low" and (stats.beta or 0) * sign > 0)


def enrich_edges_with_stats(G: nx.DiGraph, event: ExtractedEvent) -> None:
    if not data_loader.cache_available():
        raise NotImplementedError("no price cache: run scripts/fetch_prices.py and commit data/cache/")
    event_node = G.graph.get("event_node")
    for u, v, d in G.edges(data=True):
        if u == event_node:
            continue
        stats = compute_edge_stats(u, v)
        if stats is None:
            continue
        d["stats"] = stats
        if d["evidence_type"] != "llm_inferred" and _upgrade(stats, d["sign"]):
            d["evidence_type"], d["verification_status"] = "quant_verified", "supported"
            d["evidence"] = list(d.get("evidence", [])) + [{
                "source_type": "price_data", "url": None,
                "text": f"Daily-return beta {stats.beta} (t={stats.t_stat}, n={stats.n}, lag {stats.lag_days}d, stability {stats.stability}).",
            }]
