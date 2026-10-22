"""Evaluate on eval/labeled_events.json. OWNER: M4. Reports ONLY measured numbers.
Metrics: event_type accuracy, entity accuracy, share of events with >=1 path, sector recall,
sector sign accuracy (on matched sectors), evidence coverage (edges with >=1 evidence item), mean latency.
Run (offline, no LLM):  python scripts/evaluate.py          add --llm to use the LLM client."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
SIGN = {"Possible pressure": "-", "Potential benefit": "+"}


def main() -> None:
    from app.pipeline import run_analysis
    from app.schemas import AnalyzeRequest
    use_llm = "--llm" in sys.argv
    events = json.loads((ROOT / "eval" / "labeled_events.json").read_text(encoding="utf-8"))
    n = len(events)
    m = dict(type=0, entity=0, with_paths=0, sec_hit=0, sec_total=0, sign_ok=0, sign_total=0, ev_edges=0, edges=0)
    lat = []
    for ev in events:
        t0 = time.time()
        r = run_analysis(AnalyzeRequest(news=ev["news"], use_llm=use_llm, simulated=True))
        lat.append(time.time() - t0)
        if r.mode == "mock":
            print(f"{ev['id']}: pipeline fell back to mock - {r.warnings}")
            continue
        m["type"] += r.event.event_type == ev.get("expected_event_type")
        m["entity"] += (ev.get("expected_entity", "").lower() in (r.event.entity or "").lower())
        m["with_paths"] += bool(r.paths)
        got = {s.sector.split(" - ")[0]: SIGN.get(s.exposure, "?") for s in r.sectors}
        for sec in ev.get("expected_sectors_affected", []):
            m["sec_total"] += 1
            if sec in got:
                m["sec_hit"] += 1
                if sec in ev.get("expected_signs", {}):
                    m["sign_total"] += 1
                    m["sign_ok"] += got[sec] == ev["expected_signs"][sec]
        m["edges"] += len(r.edges)
        m["ev_edges"] += sum(1 for e in r.edges if e.evidence)
    pct = lambda a, b: f"{100 * a / b:.0f}% ({a}/{b})" if b else "n/a"
    print(f"events: {n}   LLM: {use_llm}")
    print("event_type accuracy :", pct(m["type"], n))
    print("entity accuracy     :", pct(m["entity"], n))
    print("events with paths   :", pct(m["with_paths"], n))
    print("sector recall       :", pct(m["sec_hit"], m["sec_total"]))
    print("sector sign accuracy:", pct(m["sign_ok"], m["sign_total"]))
    print("evidence coverage   :", pct(m["ev_edges"], m["edges"]))
    print(f"mean latency        : {sum(lat) / len(lat):.2f}s")


if __name__ == "__main__":
    main()
