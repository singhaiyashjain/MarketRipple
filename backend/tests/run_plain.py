"""Run test_graph_analysis.py without pydantic/pytest (stubs app.config). python tests/run_plain.py"""
import sys, types
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
try:
    import pydantic_settings  # noqa
except ImportError:
    cfg = types.ModuleType("app.config"); cfg.DATA_DIR = ROOT / "data"
    sys.modules["app.config"] = cfg
    sc = types.ModuleType("app.schemas"); sc.Edge = sc.ExtractedEvent = object   # only used as type hints
    sys.modules["app.schemas"] = sc
sys.path.insert(0, str(Path(__file__).parent))
import test_graph_analysis as t
fails = 0
for name in sorted(dir(t)):
    if name.startswith("test_"):
        try:
            getattr(t, name)(); print("PASS", name)
        except Exception as e:
            fails += 1; print("FAIL", name, repr(e))
sys.exit(1 if fails else 0)
