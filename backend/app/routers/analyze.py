"""POST /api/analyze, GET /api/edges/{id}, GET /api/analyses/{id}  OWNER: M3"""
import logging
import re
from fastapi import APIRouter, HTTPException
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.pipeline import run_analysis
from app.graph.seed_loader import load_seed_graph
from app.graph import store

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    resp = run_analysis(req)
    try:                                   # feeds the recurring-news alerts; must never break an analysis
        from app.recurrence import tracker
        head = re.split(r"(?<=[.!?])\s", req.news.strip(), maxsplit=1)[0][:200]
        tracker.record_event(resp.model_dump(mode="json"), head, simulated=req.simulated, kind="manual")
    except Exception:
        logging.getLogger("finpulse.recurrence").exception("could not record event")
    return resp


@router.get("/edges/{edge_id}")
def get_edge(edge_id: str):
    """Full detail of one curated (seed) edge. Quant stats appear here once M4's stage fills them."""
    G = load_seed_graph()
    for u, v, d in G.edges(data=True):
        if d["id"] == edge_id:
            return {"source": u, "target": v,
                    "source_label": G.nodes[u]["label"], "target_label": G.nodes[v]["label"], **d}
    raise HTTPException(status_code=404, detail="edge not found")


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str):
    try:
        return store.load_analysis(analysis_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="analysis not found")
    except Exception:                                    # MongoDB off or unreachable
        raise HTTPException(status_code=503, detail="analysis storage unavailable")