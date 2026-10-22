"""Decide verification_status & evidence_type (fact vs inference). OWNER: M4
Rules (first match wins) on an edge's evidence list + type:
  llm_inferred + a news quote or quant stats   -> 'supported'
  llm_inferred otherwise                       -> 'unverified'  (never presented as fact)
  evidence_type quant_verified                 -> 'supported'
  domain_rule with a domain_knowledge note     -> 'reviewed'
  news_evidence with a news quote              -> 'supported'
  anything else                                -> 'unverified'
Conflicts (quant sign opposite to edge sign) -> 'conflicting'."""
from app.schemas import Edge


def verify_data(d: dict) -> tuple[str, str]:
    """(evidence_type, verification_status) from a plain edge dict."""
    kinds = {ev["source_type"] if isinstance(ev, dict) else ev.source_type for ev in d.get("evidence", [])}
    stats, sign, etype = d.get("stats"), d.get("sign", 1), d["evidence_type"]
    beta = getattr(stats, "beta", None) if stats is not None else None
    t = getattr(stats, "t_stat", None) if stats is not None else None
    if beta is not None and sign != 0 and beta * sign < 0 and abs(t or 0) >= 2:
        return etype, "conflicting"
    if etype == "llm_inferred":
        return etype, "supported" if ("news" in kinds or "price_data" in kinds) else "unverified"
    if etype == "quant_verified":
        return etype, "supported"
    if etype == "domain_rule":
        return etype, "reviewed" if "domain_knowledge" in kinds else "unverified"
    if etype == "news_evidence":
        return etype, "supported" if "news" in kinds else "unverified"
    return etype, "unverified"


def verify_edge(edge: Edge) -> Edge:
    etype, status = verify_data(edge.model_dump())
    return edge.model_copy(update={"evidence_type": etype, "verification_status": status})
