"""Single LLM adapter + disk cache (data/llm_cache). OWNER: M2
Keep provider-specific code ONLY here so we can swap Gemini/Claude/OpenAI/Groq in minutes.

Uses plain HTTPS via httpx (already in requirements.txt) -> no provider SDK to install.
Set in .env:  LLM_PROVIDER=gemini|anthropic|openai|groq   LLM_API_KEY=...   LLM_MODEL=<model name>
"""
import hashlib
import json
import re
from typing import Any

import httpx

from app.config import DATA_DIR, settings

CACHE_DIR = DATA_DIR / "llm_cache"
TIMEOUT_S = 25.0


class LLMUnavailable(RuntimeError):
    """No provider configured, or the call/parse failed. Callers fall back to rules."""


# ---------- cache ----------
def _key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _cache_read(prompt: str):
    if not settings.use_llm_cache:
        return None
    path = CACHE_DIR / f"{_key(prompt)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    return None


def _cache_write(prompt: str, data) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{_key(prompt)}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # cache is best-effort


# ---------- parsing ----------
def parse_json_text(text: str):
    """Parse JSON from an LLM reply, tolerating ```json fences and chatter around it."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise LLMUnavailable("LLM reply contained no JSON")
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    try:
        return json.loads(text[start:end + 1])
    except ValueError as exc:
        raise LLMUnavailable(f"LLM reply was not valid JSON: {exc}") from exc


# ---------- providers (the ONLY provider-specific code) ----------
# Each call takes (prompt, key, model) so the same code serves the primary and the fallback.
def _call_gemini(prompt: str, key: str, model: str) -> str:
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    if key.startswith("AQ."):
        # Vertex AI express-mode key (not an AI Studio "AIza" key) -> Vertex endpoint
        url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent"
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = httpx.post(url, params={"key": key}, json=body, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_anthropic(prompt: str, key: str, model: str) -> str:
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    body = {"model": model, "max_tokens": 1500, "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    r = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body,
                   timeout=TIMEOUT_S)
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json()["content"])


def _call_openai_style(url: str, prompt: str, key: str, model: str) -> str:
    headers = {"Authorization": f"Bearer {key}"}
    body = {"model": model, "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    r = httpx.post(url, headers=headers, json=body, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_provider(prompt: str, provider: str | None = None, key: str | None = None,
                   model: str | None = None) -> str:
    provider = (provider or settings.llm_provider).lower()
    key = settings.llm_api_key if key is None else key
    model = settings.llm_model if model is None else model
    if provider == "gemini":
        return _call_gemini(prompt, key, model)
    if provider == "anthropic":
        return _call_anthropic(prompt, key, model)
    if provider == "openai":
        return _call_openai_style("https://api.openai.com/v1/chat/completions", prompt, key, model)
    if provider == "groq":
        return _call_openai_style("https://api.groq.com/openai/v1/chat/completions", prompt, key, model)
    raise LLMUnavailable(f"unknown LLM_PROVIDER '{provider}'")


def _providers() -> list[tuple[str, str, str]]:
    """Ordered (provider, key, model) list: primary first, then the fallback if configured."""
    out = []
    if settings.llm_provider.lower() != "none" and settings.llm_api_key and settings.llm_model:
        out.append((settings.llm_provider, settings.llm_api_key, settings.llm_model))
    if (settings.fallback_provider.lower() != "none" and settings.fallback_api_key
            and settings.fallback_model):
        out.append((settings.fallback_provider, settings.fallback_api_key, settings.fallback_model))
    return out


# ---------- public API ----------
def complete_json(prompt: str, schema_hint: dict | None = None, use_cache: bool = True) -> Any:
    """Return parsed JSON (dict or list) from the LLM. Cache key = sha256(prompt).
    Raises LLMUnavailable on any failure -> callers must have a fallback."""
    cached = _cache_read(prompt) if use_cache else None      # use_cache=False: chat prompts are one-off, keep them out of llm_cache
    if cached is not None:
        return cached

    providers = _providers()
    if not providers:
        raise LLMUnavailable("no LLM configured (set LLM_PROVIDER / LLM_API_KEY / LLM_MODEL in .env)")

    if schema_hint:
        prompt_to_send = prompt + "\n\nJSON shape hint:\n" + json.dumps(schema_hint)
    else:
        prompt_to_send = prompt

    last_err: LLMUnavailable | None = None
    data = None
    for provider, key, model in providers:
        try:
            data = parse_json_text(_call_provider(prompt_to_send, provider, key, model))
            break
        except LLMUnavailable as exc:
            last_err = exc
            print(f"[llm_client] {provider} gave unusable output: {exc}", flush=True)
        except Exception as exc:  # network, HTTP status, unexpected payload shape
            resp = getattr(exc, "response", None)
            code = getattr(resp, "status_code", "")
            detail = resp.text[:200] if resp is not None else str(exc)
            print(f"[llm_client] {provider} call failed: {type(exc).__name__} {code} {detail}", flush=True)
            last_err = LLMUnavailable(f"LLM call failed ({type(exc).__name__} {code}): {detail}")
    if data is None:
        raise last_err or LLMUnavailable("LLM call failed")

    if use_cache:
        _cache_write(prompt, data)
    return data
