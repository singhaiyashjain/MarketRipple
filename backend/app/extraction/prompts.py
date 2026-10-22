"""Prompt templates. OWNER: M2
Prompts are also the cache key (llm_client hashes the final prompt) -> after editing a prompt,
re-run the 3 demo events once with a real key to refresh data/llm_cache/ and commit it.
"""

EVENT_TYPES = ["commodity_price_shock", "interest_rate_hike", "interest_rate_cut",
               "currency_depreciation", "currency_appreciation", "geopolitical_event",
               "regulatory_change", "other"]

EXTRACT_PROMPT = """You extract ONE financial event from a news text.
Return ONLY a JSON object with exactly these keys:
event_type, entity, indicator, direction, change, change_pct, driver, country, event_date, source

Field rules:
- event_type: one of {event_types}
- entity: the main thing that moved or acted (e.g. "Crude Oil", "Reserve Bank of India", "USD/INR").
  For currency events use the pair, e.g. the Indian rupee weakening -> entity "USD/INR".
- indicator: snake_case metric, e.g. crude_oil_price, policy_repo_rate, usd_inr_exchange_rate
- direction: "increase" | "decrease" | "unchanged" | "unknown".
  Direction is of the entity/indicator itself (rupee weakening => USD/INR "increase").
- change: the change exactly as written in the text with sign, e.g. "+12%", "+25 basis points"; else null
- change_pct: the number only, as a positive float, ONLY if the text states a percentage; else null
- driver: the stated cause, copied briefly from the text; else null
- country: country concerned, only if clear from the text; else null
- event_date: only if a date is written in the text (as written); else null
- source: only if a publisher/source is named in the text; else null

Hard rules: use null for anything not stated. NEVER invent or estimate numbers or dates.
No commentary, no markdown, JSON only.

NEWS:
{news}
"""

EXPAND_PROMPT = """You are a careful financial analyst. Given an event and the existing graph nodes,
propose up to {k} ADDITIONAL plausible economic transmission links between the listed nodes that
are not obviously already covered. Use ONLY node ids from NODES for source and target.

Return ONLY a JSON object: {{"edges": [ {{"source": "<node id>", "target": "<node id>",
"relationship": "influences" | "may_pressure" | "may_benefit" | "may_influence",
"sign": 1 | -1 | 0, "horizon": "immediate" | "short" | "medium" | "long",
"explanation": "<one sentence on the mechanism>", "assumptions": ["<short assumption>"]}} ]}}

sign: +1 = target moves in the same direction as source, -1 = opposite, 0 = mixed/uncertain.
These are hypotheses, not facts: do not claim certainty and do not give probabilities.
EVENT: {event}
NODES: {nodes}
"""
