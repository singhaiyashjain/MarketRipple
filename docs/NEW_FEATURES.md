# New: recurring-news alerts (blinking stars) + historical backtest

Answers the mentor's two points:

1. **"If a star keeps getting negative / similar news, it should open and blink."**
2. **"Has this happened before? The last 5 times this happened, here is what moved."**

## How it works

### Recurring news -> blinking stars (time series over analysed events)
* Every analysed event is logged to MongoDB (`events_log` collection, same `MONGODB_URI` as saved analyses): live news and replay events
  (from the monitor) and anything analysed through `POST /api/analyze`. Canned "mock" samples are never logged.
* For each star (graph node) we look at a rolling window (default **7 days**) and count **distinct stories** that hit it
  with a **negative** effect. Near-identical headlines (word overlap >= 50%) inside 24 h count once (live news only).
* Levels: **alert** = >= 3 negative stories (red, blinks, sonar ring) · **watch** = >= 2 negative stories, or >= 3 stories
  directly about the star (amber, slow pulse). Also reported: a recency-weighted score (half-life 3 days) and a trend
  (rising / steady / easing = recent half of the window vs the earlier half).
* In the UI: the star blinks in the 3D graph; when an event is shown whose graph contains an alerting star, the camera flies
  to the strongest one and **its card opens** (once per analysis; switch off with "auto-open star"). The left panel
  "Recurring news" lists all blinking stars; the card shows the stories behind the alert and a
  **"Last 5 times this happened"** button.
* Replay / sample events are stored with a `simulated` flag, shown as "(simulated)", and can be excluded with the
  "include simulated" checkbox. "clear history" wipes the log.

### Historical backtest
* `backend/app/quant/backtest.py`, built on `quant/event_study.py`, reading only `data/cache/*.csv`.
* Driver = the event's entry node (e.g. `crude` -> `BZ=F`); direction from the event edge. Targets = affected nodes on the
  strongest paths that have a ticker in `data/tickers.json` (market proxy `^NSEI`).
* A past shock = driver day with |z| >= 2 (vs prior 60-day vol) in the same direction; shocks < 5 trading days apart merge.
* Per target: number of episodes, the **5 most recent** (date, driver move, return and market-adjusted abnormal return at
  +1/+5/+20 trading days), mean abnormal return + t-stat, hit-rate, and a verdict.
* **Verdict** "history agrees / disagrees with the graph" is only given when the +5-day average is statistically
  significant (|t| >= 2) *and* the hit-rate points the same way; otherwise it says "leans with/against the graph - not
  significant" or "inconclusive". With fewer than 3 past episodes: "insufficient history", no averages.
* If the news states a size (`change_pct`) it is compared with the historical single-day shocks (and flagged as a
  different period).
* Missing ticker / missing CSV -> `{"available": false, "reason": ...}`; nothing is ever invented.

## API
| Endpoint | Purpose |
|---|---|
| `GET /api/recurrence?window_days=7&include_simulated=true` | per-star signals: `alerts`, `watch`, `nodes{id:{level,negative,trend,score,reason,stories,drivers}}` |
| `GET /api/recurrence/{node_id}/backtest` | "last 5 times" for the shock that keeps hitting that star |
| `DELETE /api/recurrence?simulated_only=false` | clear the history |
| `POST /api/chat` body `{message, analysis_id or analysis, history?, backtest?, language?}` | grounded analyst answer with validated `cited_path_ids` / `cited_node_ids` (backend only so far) |
| `POST /api/backtest` body `{analysis_id}` or `{analysis}` (+ optional `shock_sigma` 1-4) | backtest for an analysis |

Thresholds are in `.env` (`RECUR_WINDOW_DAYS`, `RECUR_ALERT_HITS`, `RECUR_WATCH_HITS`, `RECUR_HALF_LIFE_DAYS`).

## MongoDB
Add `MONGODB_URI=` (and optionally `MONGODB_DB`) to `.env`, then `pip install -r backend/requirements.txt` (adds `pymongo`). Without a URI the app still runs: analyses are not saved and the alert log is in memory.

## Run (PowerShell, from the project root)
```powershell
python scripts/fetch_prices.py            # once; fills data/cache (already done if you see the CSVs)
cd backend
python -m uvicorn app.main:app --reload --port 8000
# second window
cd frontend
npm install        # first time only
npm run dev        # http://localhost:5173
```
**Demo in 30 seconds:** tick "Replay demo mode" (or press "Fire next saved event" several times). Oil and rupee
stories both hurt airline stars, so after a few events the airline stars start blinking and one of them opens by itself.
Click "Last 5 times this happened" on its card (or open "Has this happened before?" in the right panel).

Tests: `cd backend; python -m pytest -q` (new: `test_backtest.py`, `test_recurrence.py`; they use synthetic prices
and a temporary database, never the network).

## Known limits (be upfront about these)
* Alerts are only as good as the event stream: the monitor analyses a few headlines per poll and only counts stories the
  graph can map. Stories the graph cannot map are not counted.
* "Negative effect" is the graph's label for that star, not a price forecast.
* A "story" = one analysed event. Different outlets reporting the same thing are merged only when their headlines overlap >= 50%.
* Backtest: proxy tickers (futures/indices), daily data, small samples, overlapping effects, no causation. Shocks in the
  last 20 trading days are excluded (outcome incomplete). The abnormal return uses a market model on `^NSEI`; targets
  that *are* the market show raw returns only. Nodes without a ticker (e.g. inflation, bond yields) cannot be tested.
* Three tickers are missing from the cache (`^CNXAUTO`, `^CNXFMCG`, `^CNXREALTY`); targets using them are listed as "not tested".
* Storage is MongoDB (`store.py` restored to Mongo; analysis ids are ObjectId strings). Verified only against a fake MongoDB (mongomock) - not against a real server.
