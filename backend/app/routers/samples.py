"""GET /api/samples  OWNER: M3"""
import json
from fastapi import APIRouter
from app.config import DATA_DIR

router = APIRouter()


@router.get("/samples")
def samples():
    return json.loads((DATA_DIR / "sample_events.json").read_text(encoding="utf-8"))
