"""Seed graph + hierarchy must stay valid (same checks as scripts/validate_seed.py)."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_seed.py"


def test_seed_data_valid():
    spec = importlib.util.spec_from_file_location("validate_seed", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0
