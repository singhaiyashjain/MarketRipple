"""Pre-compute full responses for the sample events -> data/demo_cache/<id>.json. OWNER: M3/M4
Run once with the LLM key set (and again offline to check), then COMMIT data/demo_cache/ so the
live demo works even if the network or the API fails.   python scripts/build_demo_cache.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    from app.pipeline import run_analysis
    from app.schemas import AnalyzeRequest
    out = ROOT / "data" / "demo_cache"
    out.mkdir(exist_ok=True)
    for s in json.loads((ROOT / "data" / "sample_events.json").read_text(encoding="utf-8")):
        r = run_analysis(AnalyzeRequest(news=s["news"], simulated=bool(s.get("simulated"))))
        (out / f"{s['id']}.json").write_text(r.model_dump_json(indent=2), encoding="utf-8")
        print(f"{s['id']}: mode={r.mode} paths={len(r.paths)} warnings={len(r.warnings)}")


if __name__ == "__main__":
    main()
