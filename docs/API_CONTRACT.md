# API Contract (v0.1)

Source of truth: `backend/app/schemas.py` (Pydantic). Canned example: `contracts/sample_response.json`.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/samples` | curated demo events (`data/sample_events.json`) |
| POST | `/api/analyze` | `{news, use_llm?, simulated?}` → `AnalyzeResponse` |
| GET | `/api/edges/{edge_id}` | (later) full evidence + quant stats for one edge |

## AnalyzeResponse
- `mode`: `live` (all stages real) · `fallback` (LLM down, rules used) · `mock` (canned)
- `event`: extracted event (`is_simulated` must be true for made-up numbers)
- `nodes[]`: `id,label,type,sector?,effect` — effect ∈ positive|negative|mixed|neutral|unknown
- `edges[]`: `id,source,target,relationship,sign(+1/-1/0),weight(0-1),evidence_type,verification_status,horizon,explanation,assumptions[],evidence[],stats?`
- `paths[]`: `id,node_ids[],edge_ids[],strength,terminal_effect,horizon,explanation,uncertainty`
- `sectors[]`: `sector,exposure,reason,confidence`
- `warnings[]`, `meta{}`

## Enums
- `evidence_type`: `domain_rule | news_evidence | llm_inferred | quant_verified`
- `verification_status`: `reviewed | supported | unverified | conflicting`
- `horizon`: `immediate | short | medium | long`
- Edge style in UI: solid = rule/verified, dashed = llm_inferred, thick = high strength.

## Rules
- `strength` = product of edge weights (relative, NOT a probability).
- `weight`/`stats.*` must come from a rubric or data; never hand-typed arbitrary numbers for live output.
- `stats` (quant) = `{beta,t_stat,n,lag_days,ci_low,ci_high,stability,note}`; absent if no data.
