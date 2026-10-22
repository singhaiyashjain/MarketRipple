import json
from app.config import CONTRACTS_DIR
from app.schemas import AnalyzeResponse


def test_sample_response_matches_schema():
    data = json.loads((CONTRACTS_DIR / "sample_response.json").read_text(encoding="utf-8"))
    resp = AnalyzeResponse(**data)
    ids = {n.id for n in resp.nodes}
    for e in resp.edges:
        assert e.source in ids and e.target in ids
    eids = {e.id for e in resp.edges}
    for p in resp.paths:
        assert set(p.node_ids) <= ids and set(p.edge_ids) <= eids
