"""Quick LLM connectivity check. Run from the repo root:  python scripts/check_llm.py
Tests the primary AND the fallback provider with the app's own code, printing real errors."""
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
from app.config import settings  # noqa: E402
from app.extraction import llm_client  # noqa: E402

targets = [("PRIMARY", settings.llm_provider, settings.llm_api_key, settings.llm_model),
           ("FALLBACK", settings.fallback_provider, settings.fallback_api_key, settings.fallback_model)]
for label, provider, key, model in targets:
    print(f"== {label}: provider={provider!r} model={model!r} "
          f"key={(key[:6] + '...' + key[-4:]) if key else 'EMPTY'}")
    if provider.lower() == "none" or not key:
        print("   not configured, skipped\n")
        continue
    try:
        out = llm_client._call_provider('Return ONLY this JSON: {"ok": true}', provider, key, model)
        print("   SUCCESS ->", out.strip()[:100], "\n")
    except httpx.HTTPStatusError as e:
        print(f"   HTTP {e.response.status_code}: {e.response.text[:500]}\n")
    except Exception as e:
        print(f"   {type(e).__name__}: {e}\n")
