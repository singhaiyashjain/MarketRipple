# Build order & checklists (tick as you go)

## M1 — Frontend (`frontend/`)
- [ ] 1. Run with mock (`VITE_USE_MOCK=true`) — page renders sample
- [ ] 2. `NewsInput` + sample picker → calls `/api/analyze`
- [ ] 3. `ImpactGraph`: dagre left→right layout, color by effect, dashed for llm_inferred
- [ ] 4. Click node → highlight neighbours; click path in `PathList` → highlight chain
- [ ] 5. `EvidencePanel`: edge explanation, evidence, assumptions, quant stats badge
- [ ] 6. `SectorTable` + `EventSummary` + `Legend`
- [ ] 7. Loading / error / "mock mode" banner; polish; responsive

## M2 — AI/NLP (`extraction/`, `explain/`, `graph/expander.py`)
- [x] 1. `llm_client.complete_json` (one provider + disk cache)
- [x] 2. `prompts.py` + `extractor.extract_event` (schema-validated, no invented numbers/dates)
- [x] 3. `fallback.rule_based_extract` (regex/keywords, works offline)
- [x] 4. `normalizer` (aliases: "Brent", "crude" → "Crude Oil Prices")
- [x] 5. `expander.propose_edges` (LLM suggests edges missing from seed; tagged `llm_inferred`)
- [x] 6. `explainer` (template first, LLM polish optional)

## M3 — Backend/Graph (`graph/`, `impact/`, `pipeline.py`, `routers/`)
- [x] 1. `seed_loader` loads `data/seed_*.json` into NetworkX DiGraph
- [x] 2. `builder.build_graph` (seed + event node + expansion)
- [x] 3. `impact.engine.find_paths` (bounded, sign-aware, top-k)
- [x] 4. `scoring` (path strength = product of weights; sign propagation)
- [x] 5. `sectors.summarize_sectors`, `horizon`
- [x] 6. `store` (SQLite persistence), wire `pipeline`, remove mock fallback per stage

## M4 — Data/Quant/Eval (`quant/`, `evidence/`, `data/`, `eval/`)
- [ ] 1. Grow `data/seed_nodes.json` / `seed_edges.json` (target ~100 nodes / 200 edges, India-focused)
- [ ] 2. `scripts/fetch_prices.py` → `data/cache/*.csv` (commit them)
- [ ] 3. `quant.data_loader`, `shock.shock_zscore`
- [ ] 4. `event_study.run_event_study` + `betas.estimate_beta`
- [ ] 5. `edge_stats.compute_edge_stats` (fills `edge.stats`, upgrades to `quant_verified`)
- [ ] 6. `evidence.attach_evidence` / `verifier`
- [ ] 7. `eval/labeled_events.json` (15 events) + `scripts/evaluate.py` + tests for 3 scenarios (oil, rate hike, INR)
- [ ] 8. (stretch) `portfolio.scenario_pnl`

## Everyone, last 3 hours
Freeze features · deploy · rehearse `docs/DEMO_SCRIPT.md` · cache the 3 demo events.
