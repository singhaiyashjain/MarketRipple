# PROGRESS (resume from the first unticked item)

Mentor requirements: **(1) graph algorithms, (2) hierarchy maintenance.**
Env note: pydantic/fastapi were NOT installable where this was written, so new graph code is
plain NetworkX and is tested with `python backend/tests/run_plain.py`; run `pytest` locally for the rest.

## Mentor features
- [x] 1. data/hierarchy.json            sector tree (Economy > group > sector > node)
- [x] 2. graph/hierarchy.py             load tree, ancestors, roll-up of path impacts
- [x] 3. graph/maintenance.py           validate tree, attach new nodes under a parent, merge duplicates
- [x] 4. impact/layers.py               BFS impact order, Dijkstra best path, PageRank/betweenness influence
- [x] 5. pipeline.py                    put results in resp.meta["graph_analysis"] (contract unchanged)
- [x] 6. tests (plain)                  backend/tests/run_plain.py + test_graph_analysis.py

## Finish M4 stubs
- [x] 7. quant/data_loader, shock, betas, event_study, edge_stats, portfolio
- [x] 8. evidence/evidence.py, verifier.py
- [x] 9. scripts: validate_seed, fetch_prices, evaluate, build_demo_cache

## Frontend
- [x] 10. types.js, api mock, contracts/sample_response.json meta.graph_analysis
- [x] 11. components/HierarchyPanel.jsx + InfluencePanel.jsx, layer badges, wire in App.jsx

## Cleanup
- [x] 12. delete stray files (main.py, timepass.py, frontend~...), update README/docs

## NOT verified (could not run in the authoring environment: no pydantic/fastapi/internet)
- [ ] A. `pytest` full suite incl. test_api, test_contract (new `meta.graph_analysis` must pass schema: meta is a free dict, should be fine)
- [ ] B. `python scripts/fetch_prices.py` then check every ticker in data/tickers.json loads; fix bad symbols
- [ ] C. `quant/edge_stats.py` end-to-end on real prices (unit tests only cover betas/shock/event_study/portfolio)
- [ ] D. `scripts/evaluate.py` and `build_demo_cache.py` run for real; eval/labeled_events.json now has 15 hand-set events (oil x5, RBI x4, Fed x2, INR x4) - review labels, then run evaluate.py
- [~] E. Seed grown 56->61 nodes, 79->84 edges (added HDFC Bank, ICICI, Infosys, UltraTech, Bajaj Finance). Target ~100/200 still open (M4)
- [x] F. Assumptions filled on all edges (validate_seed: 0 warnings). M4 should review wording
- [ ] G. Frontend vs live backend (not mock): check graph_analysis renders; then deploy

## Notes
- New tickers (HDFCBANK.NS, ICICIBANK.NS, INFY.NS, ULTRACEMCO.NS, BAJFINANCE.NS) are unverified: run fetch_prices.py and fix any that fail.
- data/member4_dropin/data/* is an unused copy of the seed files; kept in sync, safe to delete.
- Offline rule-based extraction only recognises RBI/Fed, rupee and crude events, so the labelled set covers those; other news needs the LLM.
- Live demo output for rate events will now also show HDFC/ICICI/Infosys etc. as terminal nodes.

## Live monitor (added)
- backend/app/live/{feeds,newsapi,monitor}.py, routers/live.py, lifespan hook in main.py, new settings in config.py / .env.example
- Region filter India | Global | All on headlines + detected events; English-only (non-Latin script items dropped in backend and frontend)
- frontend: LivePanel, HeadlineTicker, RippleBar, hooks useLiveEvents/useHeadlines, NewsInput `injected`, ImpactGraph `revealOrder`
- NOT verified: real RSS URLs (feeds change; edit backend/app/live/feeds.py), full backend run (fastapi not installable where this was written), `npm run build`

## Live news in every region (update)
- Every region (India | Global | All) now has its own current-news list: new `components/NewsFeedPanel.jsx` (left column, under Live monitor). Click a story = analyse it; stories already auto-analysed show "Impact ready" and open their graph.
- Backend `get_headlines` now returns per-story `relevant` (market-moving) and `event_version`, plus `counts` per region.
- Auto-detected events use a PER-REGION quota (`LIVE_MAX_EVENTS_PER_POLL` is now per region, `live_max_attempts_per_region` caps tries), so India and Global both get events instead of one starving the other.
- More feeds: Google News India/World (business + markets/economy searches) + MarketWatch. Google News items use their real publisher as `source`.
- Bug fixed: feed publish dates were all read as "now" (XML element truthiness), which broke sorting and "x min ago". 
- NOT verified here (no internet / deps): live RSS URLs, `npm run build`, full backend run. Run locally and check "RSS feeds x/y responding" in Live monitor.

## No more sample data for live news (update)
- Stories the graph cannot map (no impact path) used to return the canned "Crude Oil +12%" sample. `pipeline._mock(..., unmapped=True)` now tags them (`meta.unmapped`) and the UI shows a "not mapped to the impact graph" card with no graph instead.
- App now auto-opens the latest REAL detected event on startup, and when you switch India / Global / All it opens that region's newest event.
- The sample response is only used for FORCE_MOCK, VITE_USE_MOCK and the "Try a sample" buttons.

## UI polish + live-news merge (update)
- Merged the live-news branch (per-region news feed, extra feeds, unmapped-story handling) into the dark 3D version. The old light-theme/2D files from that branch were NOT carried over.
- 3D graph: constant-size crisp labels, slower link particles, eased camera/selection transitions, legend moved top-right (short version).
- Right panel: 3/5 of the screen, translucent layered overlay, collapsible; scene re-centres in the clear area (width is `--rp-w` in `frontend/src/index.css`).
- NOT verified here: `npm run build` / browser run, backend tests (no deps installed where this was merged).
