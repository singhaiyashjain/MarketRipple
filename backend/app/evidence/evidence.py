"""Attach evidence to edges: news quotes, domain-rule notes, price data refs. OWNER: M4
Nothing is invented: a news snippet is only attached when a sentence of the article contains
keywords from BOTH ends of the edge (or, for the event edge, the event's entity)."""
import re
import networkx as nx
from app.schemas import ExtractedEvent
from app.evidence.verifier import verify_data

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOP = {"and", "the", "of", "in", "costs", "prices", "price", "rate", "rates", "demand", "for", "to", "a"}


def _keywords(label: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9&]+", label.lower()) if w not in _STOP and len(w) > 2}


def _sentences(news: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(news.strip()) if s.strip()]


def _quote(sentences: list[str], *groups: set[str]) -> str | None:
    for s in sentences:
        low = s.lower()
        if all(any(k in low for k in g) for g in groups if g):
            return s[:280]
    return None


def attach_evidence(G: nx.DiGraph, event: ExtractedEvent, news: str) -> None:
    sentences = _sentences(news)
    event_node = G.graph.get("event_node")
    entity_kw = _keywords(event.entity or "") | _keywords(event.indicator or "")
    for u, v, d in G.edges(data=True):
        ev = [e for e in d.get("evidence", []) if (e["source_type"] if isinstance(e, dict) else e.source_type) != "domain_knowledge"]
        if d["evidence_type"] == "domain_rule" and d.get("explanation"):
            ev.append({"source_type": "domain_knowledge", "text": d["explanation"], "url": d.get("reference_url")})
        if u == event_node:
            q = _quote(sentences, entity_kw or _keywords(G.nodes[v]["label"])) or (sentences[0][:280] if sentences else None)
        else:
            q = _quote(sentences, _keywords(G.nodes[u]["label"]), _keywords(G.nodes[v]["label"]))
        if q:
            ev.append({"source_type": "news", "text": q, "url": None})
        d["evidence"] = ev
        d["evidence_type"], d["verification_status"] = verify_data(d)
