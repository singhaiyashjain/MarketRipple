"""event -> graph: seed + event node + optional LLM expansion. OWNER: M3

Output graph conventions (other stages rely on these):
  G.graph["event_node"]  -> id of the event node (type 'event')
  G.graph["warnings"]    -> list[str] shown in the UI
  edge attrs             -> see seed_loader
"""
import re
import networkx as nx
from app.schemas import ExtractedEvent
from app.graph.seed_loader import load_seed_graph
from app.extraction.normalizer import normalize_entity
from app.graph.linker import NodeLinker, infer_direction

# LLM-proposed edges are unverified, so they may never look stronger than this.
LLM_EDGE_WEIGHT_CAP = 0.4

# (regex on normalised text, seed node id) - first match wins, order matters.
# Word-bounded: "oil" used to match inside turmoil/soil/boil and "repo" inside report.
_NOT_CRUDE = (r"(?<!palm )(?<!edible )(?<!olive )(?<!vegetable )(?<!cooking )(?<!mustard )(?<!coconut )"
              r"(?<!sunflower )(?<!soybean )(?<!soya )(?<!groundnut )(?<!castor )(?<!essential )")
KEYWORD_TO_NODE: list[tuple[str, str]] = [
    (r"\bpolicy (?:interest |repo )?rates?\b|\brepo\b|\binterest rates?\b|\brate (?:hike|cut)s?\b|\bmonetary policy\b", "policy_rate"),
    (r"\b(?:crude|brent|wti|opec)\b|" + _NOT_CRUDE + r"\boil\b(?! india\b| and natural gas\b| & natural gas\b)", "crude"),
    (r"\busd/?inr\b|\brupee\b|\binr\b|\bcurrency\b", "usdinr"),
    (r"\binflation\b|\bcpi\b", "inflation"),
    (r"\bbond yields?\b|\bg-?secs?\b", "bond_yields"),
    (r"\bfii\b|\bfpi\b|\bforeign (?:portfolio|investor)", "fii_flows"),
    (r"\bnifty\b", "nifty"),
    (r"\breserve bank\b|\brbi\b", "rbi"),
]

def _clean(text: str | None) -> str:
    return (text or "").replace("_", " ").strip().lower()


def match_seed_node(event: ExtractedEvent, G: nx.DiGraph) -> tuple[str | None, str, float]:
    """Map the extracted event to a seed node -> (node_id, method, score).
    1) exact label/id  2) keyword rules  3) NLP semantic linking (TF-IDF cosine) as the fallback."""
    for raw in (event.indicator, event.entity, event.event_type):
        if not raw:
            continue
        norm = normalize_entity(raw)
        for nid, attrs in G.nodes(data=True):               # exact label / id match
            if norm.lower() == attrs.get("label", "").lower() or _clean(norm) == nid:
                return nid, "exact", 1.0
        text = _clean(norm)
        for pattern, nid in KEYWORD_TO_NODE:
            if nid in G and re.search(pattern, text):
                return nid, "keyword", 1.0
    query = " ".join(x for x in (event.indicator, event.entity, event.driver, event.event_type) if x)
    nid, score = NodeLinker(G).link(query)
    return (nid, "nlp_semantic", score) if nid else (None, "none", score)

def _event_sign(event: ExtractedEvent, node_id: str) -> tuple[int, str | None]:
    """+1 if the matched node goes UP, -1 if DOWN. Returns (sign, warning)."""
    d = event.direction
    text = " ".join(_clean(x) for x in (event.event_type, event.entity, event.indicator))
    if node_id == "usdinr":
        # the node is USD/INR: depreciation of the rupee = USD/INR UP
        if re.search(r"deprec|weak|fall|record low|slump", text):
            return 1, None
        if re.search(r"apprec|strength|gain", text):
            return -1, None
        if d == "decrease" and re.search(r"rupee|\binr\b", text) and "usd" not in text:
            return 1, None          # "rupee falls" == USD/INR rises
    if d == "increase":
        return 1, None
    if d == "decrease":
        return -1, None
    return 1, "Event direction unknown - assuming an increase."


def _event_label(event: ExtractedEvent, node_label: str) -> str:
    move = event.change or {"increase": "up", "decrease": "down"}.get(event.direction or "", "move")
    return f"{node_label} {move}"


def build_graph(event: ExtractedEvent, use_llm: bool = True) -> nx.DiGraph:
    G = load_seed_graph()
    G.graph["warnings"] = []
    G.graph["event_node"] = None

    target, method, score = match_seed_node(event, G)
    G.graph["link"] = {"node": target, "method": method, "score": score}
    if target is None:
        G.graph["warnings"].append(
            f"Could not map event '{event.entity}' to the knowledge graph - no impact paths.")
        return G

    if method == "nlp_semantic":
        G.graph["warnings"].append(
            f"Event linked to '{G.nodes[target]['label']}' by NLP similarity (score {score}); please verify.")
    if not event.direction or event.direction == "unknown":       # NLP fallback when the extractor gave none
        guess = infer_direction(event.change, event.driver, event.event_type, event.entity)
        if guess:
            event.direction = guess
    sign, warn = _event_sign(event, target)
    if warn:
        G.graph["warnings"].append(warn)

    ev_id = f"ev_{target}"
    G.add_node(ev_id, label=_event_label(event, G.nodes[target]["label"]), type="event", sector=None)
    G.add_edge(
        ev_id, target,
        id="e_event", relationship="triggers", sign=sign, weight=1.0,
        evidence_type="news_evidence", verification_status="supported", horizon="immediate",
        explanation="The news item reports this event; it is the starting point of the analysis.",
        assumptions=[], evidence=[], stats=None,           # M4's attach_evidence adds the quote
    )
    G.graph["event_node"] = ev_id

    if use_llm:
        _expand_with_llm(G, event)
    return G


def _expand_with_llm(G: nx.DiGraph, event: ExtractedEvent) -> None:
    from app.graph import expander
    try:
        proposals = expander.propose_edges(event, G)
    except NotImplementedError:
        G.graph["warnings"].append("LLM edge expansion not available - using curated graph only.")
        return
    except Exception as exc:                                # LLM down / bad JSON must not kill the demo
        G.graph["warnings"].append(f"LLM edge expansion failed ({type(exc).__name__}) - curated graph only.")
        return

    used_ids = {d["id"] for _, _, d in G.edges(data=True)}
    added = 0
    for e in proposals:
        if e.source not in G or e.target not in G or e.source == e.target or G.has_edge(e.source, e.target):
            continue                                        # only link existing nodes; never overwrite a rule
        eid = e.id if e.id not in used_ids else f"x{added + 1}_{e.id}"
        used_ids.add(eid)
        G.add_edge(
            e.source, e.target,
            id=eid, relationship=e.relationship, sign=e.sign,
            weight=min(e.weight, LLM_EDGE_WEIGHT_CAP),
            evidence_type="llm_inferred", verification_status="unverified",   # forced, whatever M2 sent
            horizon=e.horizon, explanation=e.explanation,
            assumptions=list(e.assumptions), evidence=[ev.model_dump() for ev in e.evidence], stats=None,
        )
        added += 1
    if added:
        G.graph["warnings"].append(f"{added} model-inferred link(s) added (dashed, unverified).")
