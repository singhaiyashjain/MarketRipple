# data/
- `seed_nodes.json`, `seed_edges.json` — curated trusted graph (**56 nodes / 79 edges**, India-focused; grow toward ~100 / 200 only with reviewed edges). Owner M4.
- `tickers.json` — node id -> yfinance ticker for quant edge stats (proxies; see its `_note`).
- `sample_events.json` — curated demo events (label simulated ones!).
- `cache/` — price CSVs from `scripts/fetch_prices.py` (commit them).
- `llm_cache/` — cached LLM responses so demos work offline (commit them).
- `demo_cache/` — full pre-computed responses for the sample events, from `scripts/build_demo_cache.py` (commit them).

## Node fields
`id, label, type, sector, polarity`
- `type` ∈ event · commodity · indicator · sector · company · index · currency · policy · country
- `polarity` — is an INCREASE of this variable good or bad for its sector?
  **+1** good (revenue, margins, demand, prices of equities) · **−1** bad (costs, inflation, borrowing cost, geopolitical risk) · **0** ambiguous (USD/INR, rates, policy nodes, crude itself).
  A path's sign says which way the end variable moves; `effect = direction × polarity` says whether that is good or bad.
  Nodes with polarity 0 are never used as the end-point of a sector-exposure statement.
- Company nodes (`type: company`) are illustrative exposures through a sector, **not recommendations**.

## Edge fields
`id, source, target, relationship, sign(+1/−1/0), weight(0–1, from rubric), evidence_type, horizon, explanation, assumptions[]`
- `sign`: +1 target moves the same way as source · −1 opposite · 0 mixed/uncertain.
- Optional: `reference` (+ `reference_url`) — a citable source, shown in the evidence panel. Add only real, checked sources.

## Weight rubric (document any change here)
| Weight | Meaning |
|---|---|
| 0.95 | definitional (an institution sets the variable, e.g. RBI sets the repo rate) |
| 0.9 | near-mechanical link |
| 0.7 | strong, well-established |
| 0.5 | moderate / conditional |
| 0.3 | weak / indirect |
| 0.8 / 0.6 / 0.4 | between the tiers above |

Weights are a **relative rubric score**, not a probability. Path strength = product of weights.

## Rules for editing the graph
1. Run `python scripts/validate_seed.py` and `pytest backend/tests/test_seed_data.py` before every commit.
2. One causal claim per edge, with an explanation a judge could read aloud and at least one assumption where it can fail.
3. Prefer first-order links. Avoid edges that create long circular feedback loops (they produce contradictory paths). The one known cycle is `import_costs → cad → usdinr → import_costs`; the path engine must use simple paths (no repeated node).
4. Removed on purpose: `policy_rate → usdinr` (it created a weak 5-hop path claiming a rate *hike* lowers borrowing costs). Edge ids are not reused, so `s56` is intentionally absent.
5. Every edge starts as `domain_rule`; it only becomes `quant_verified` when `quant.edge_stats` finds significant, stable, same-sign historical data.

---
## Graph algorithms & hierarchy (mentor requirements)
| Need | Where | What it does |
|---|---|---|
| Graph algorithms | `backend/app/impact/layers.py` | BFS impact order (1st/2nd/3rd-order), Dijkstra strongest chain per sector (cost = -log weight = max product of weights), betweenness + PageRank to rank key transmission nodes. `impact/engine.py` keeps the bounded `all_simple_paths` enumeration. |
| Hierarchy | `data/hierarchy.json`, `backend/app/graph/hierarchy.py` | Economy > group > sector > node; `roll_up()` aggregates path impact up the tree. |
| Hierarchy maintenance | `backend/app/graph/maintenance.py`, `scripts/validate_seed.py` | validate tree vs nodes, attach new nodes under a sector without duplicates, reject unknown sectors. |
| Output | `response.meta.graph_analysis` | Optional field; contract unchanged. UI: `HierarchyPanel.jsx`, `InfluencePanel.jsx`. |

Tests: `pytest` (full) or `python backend/tests/run_plain.py` (graph/evidence tests, no pydantic needed).
Before demo: `python scripts/fetch_prices.py` (needs internet, then commit `data/cache/`), `python scripts/build_demo_cache.py`, `python scripts/evaluate.py`.


## Recurring-news alerts + historical backtest
Stars that keep getting negative news blink and open; every analysis can be checked against 10 years of prices ("the last 5 times this happened"). See [docs/NEW_FEATURES.md](docs/NEW_FEATURES.md).
