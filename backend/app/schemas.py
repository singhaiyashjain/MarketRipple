"""Pydantic models = the API contract. Keep in sync with contracts/ and frontend/src/types.js.
OWNER: everyone (changes need all-hands OK)."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

Effect = Literal["positive", "negative", "mixed", "neutral", "unknown"]
NodeType = Literal["event", "commodity", "indicator", "sector", "company", "index",
                   "currency", "policy", "country"]
EvidenceType = Literal["domain_rule", "news_evidence", "llm_inferred", "quant_verified"]
Verification = Literal["reviewed", "supported", "unverified", "conflicting"]
Horizon = Literal["immediate", "short", "medium", "long"]
Mode = Literal["live", "fallback", "mock"]


class AnalyzeRequest(BaseModel):
    news: str = Field(min_length=10, max_length=10000)
    use_llm: bool = True
    simulated: bool = False          # true => numbers are made-up demo values


class ExtractedEvent(BaseModel):
    event_type: str
    entity: str
    indicator: Optional[str] = None
    direction: Optional[Literal["increase", "decrease", "unchanged", "unknown"]] = None
    change: Optional[str] = None      # as written in source, e.g. "+12%"
    change_pct: Optional[float] = None
    driver: Optional[str] = None
    country: Optional[str] = None
    event_date: Optional[str] = None  # only if present in the source text
    source: Optional[str] = None
    is_simulated: bool = False


class Node(BaseModel):
    id: str
    label: str
    type: NodeType
    sector: Optional[str] = None
    effect: Effect = "unknown"


class Evidence(BaseModel):
    source_type: str                  # news | domain_knowledge | price_data | llm
    text: str
    url: Optional[str] = None


class EdgeStats(BaseModel):
    beta: Optional[float] = None
    t_stat: Optional[float] = None
    n: Optional[int] = None
    lag_days: Optional[int] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    stability: Optional[Literal["low", "medium", "high"]] = None
    note: Optional[str] = None


class Edge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    sign: Literal[-1, 0, 1] = 1       # +1 same direction, -1 opposite, 0 mixed
    weight: float = Field(ge=0, le=1)
    evidence_type: EvidenceType
    verification_status: Verification = "unverified"
    horizon: Horizon = "short"
    explanation: str = ""
    assumptions: list[str] = []
    evidence: list[Evidence] = []
    stats: Optional[EdgeStats] = None


class ImpactPath(BaseModel):
    id: str
    node_ids: list[str]
    edge_ids: list[str]
    strength: float                   # relative path strength (product of weights), NOT a probability
    terminal_effect: Effect
    horizon: Horizon
    explanation: str = ""
    uncertainty: str = ""


class SectorExposure(BaseModel):
    sector: str
    exposure: str
    reason: str
    confidence: Literal["low", "medium", "high"] = "low"


class AnalyzeResponse(BaseModel):
    mode: Mode
    event: ExtractedEvent
    nodes: list[Node]
    edges: list[Edge]
    paths: list[ImpactPath]
    sectors: list[SectorExposure]
    warnings: list[str] = []
    meta: dict = {}
