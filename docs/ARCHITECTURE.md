# Architecture

```
frontend (React/Cytoscape) ──/api/analyze──► FastAPI
                                              │ pipeline.run_analysis
   extraction.extractor  ── LLM (cached) / rule fallback ──► ExtractedEvent
   graph.builder         ── seed graph (data/seed_*.json) + expander.propose_edges (LLM, tagged llm_inferred)
   impact.engine         ── sign-aware bounded path search, top-k by strength
   evidence.*            ── attach quotes/rules, verify, label fact vs inference
   quant.edge_stats      ── event study / beta / lag from cached prices → edge.stats
   impact.sectors        ── group terminal nodes into sector exposure
   explain.explainer     ── plain-English explanation per path/edge
```
Principles: LLM structures text and *proposes*; graph + rules *decide structure*; quant *verifies with data*; UI *shows uncertainty*. Bounded paths (≤5 hops), ≤25 nodes visible. Deterministic fallback everywhere.
