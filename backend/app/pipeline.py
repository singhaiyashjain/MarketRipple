"""Orchestrator. Each stage is owned by a different person.  OWNER: M3

- extraction not ready  -> whole response is the canned sample (mode='mock').
- graph + impact + sectors (M3) are required.
- evidence / quant / explain are OPTIONAL stages: if a teammate's stub still raises
  NotImplementedError (or crashes) the stage is skipped, a warning is added and the rest
  of the real pipeline still runs. meta.stages_real / meta.stages_mock tell the UI what is real.
"""
import json
import logging
from app.config import CONTRACTS_DIR, settings
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.extraction.extractor import extract_event
from app.graph.builder import build_graph
from app.graph.serialize import graph_to_nodes_edges
from app.graph import store
from app.impact.engine import find_paths
from app.impact.sectors import summarize_sectors
from app.impact.layers import analyse as analyse_graph
from app.graph.hierarchy import roll_up
from app.graph.maintenance import validate_hierarchy
from app.evidence.evidence import attach_evidence
from app.quant.edge_stats import enrich_edges_with_stats
from app.explain.explainer import explain_paths

log = logging.getLogger("finpulse.pipeline")


def _mock(req: AnalyzeRequest, reason: str, unmapped: bool = False) -> AnalyzeResponse:
    data = json.loads((CONTRACTS_DIR / "sample_response.json").read_text(encoding="utf-8"))
    data["warnings"] = [f"Mock data: {reason}"]
    data["event"]["is_simulated"] = True
    # unmapped=True: the story is real but the graph has no path for it. The UI must NOT present this
    # canned sample as the story's result (it shows a "not mapped" message instead).
    data["meta"] = {**(data.get("meta") or {}), "unmapped": unmapped, "unmapped_reason": reason if unmapped else None}
    return AnalyzeResponse(**data)

def _unmapped(event, reason: str) -> AnalyzeResponse:
    """Real story, but the graph has no path for it. Return an EMPTY result with the real event,
    never the canned crude-oil sample."""
    return AnalyzeResponse(
        mode="mock", event=event, nodes=[], edges=[], paths=[], sectors=[],
        warnings=[f"Not mapped: {reason}"],
        meta={"stages_real": ["extraction"], "stages_mock": [], "unmapped": True, "unmapped_reason": reason},
    )
def run_analysis(req: AnalyzeRequest) -> AnalyzeResponse:
    if settings.force_mock:
        return _mock(req, "FORCE_MOCK=true")

    try:
        event = extract_event(req.news, use_llm=req.use_llm)
    except NotImplementedError:
        return _mock(req, "stage 'extraction' not implemented yet")
    event.is_simulated = event.is_simulated or req.simulated

    G = build_graph(event, use_llm=req.use_llm)
    warnings: list[str] = list(G.graph.get("warnings", []))
    paths = find_paths(G, event)
    if not paths:
        return _unmapped(event, "no impact paths found for this event: " + " ".join(warnings))
    real, skipped = ["extraction", "graph", "impact"], []

    def optional(name: str, fn):
        try:
            result = fn()
            real.append(name)
            return result
        except NotImplementedError:
            skipped.append(name)
        except Exception as exc:                          # a teammate's bug must not kill the demo
            log.exception("stage %s failed", name)
            skipped.append(name)
            warnings.append(f"Stage '{name}' failed ({type(exc).__name__}); skipped.")
        return None

    optional("evidence", lambda: attach_evidence(G, event, req.news))
    optional("quant", lambda: enrich_edges_with_stats(G, event))
    explained = optional("explain", lambda: explain_paths(G, paths))
    paths = explained or paths

    sectors = summarize_sectors(G, paths)
    nodes, edges = graph_to_nodes_edges(G, paths)
    if skipped:
        warnings.append("Not yet available: " + ", ".join(skipped))

    graph_analysis = None
    try:                                  # mentor features: BFS order, best paths, centrality, hierarchy
        graph_analysis = analyse_graph(G, G.graph["event_node"], {n.id for n in nodes})
        graph_analysis["hierarchy"] = roll_up(G, paths)
        graph_analysis["hierarchy_problems"] = validate_hierarchy(G)
    except Exception:
        log.exception("graph analysis failed")
        warnings.append("Graph analysis (layers/centrality) unavailable.")

    resp = AnalyzeResponse(
        mode="live" if not skipped else "fallback", event=event, nodes=nodes, edges=edges,
        paths=paths, sectors=sectors, warnings=warnings,
        meta={"stages_real": real, "stages_mock": skipped, "entity_link": G.graph.get("link"),
              "graph_analysis": graph_analysis},
    )
    try:
        resp.meta["analysis_id"] = store.save_analysis(resp.model_dump())
    except RuntimeError as exc:                                   # MongoDB not configured / in back-off: simply not saved
        log.debug("analysis not saved: %s", exc)
    except Exception:
        log.exception("could not persist analysis")
    return resp
