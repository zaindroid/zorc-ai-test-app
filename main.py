"""zorc-ai-test-app -- throwaway repo, exists only to prove ai: true in
app.yaml actually results in a real, working LLM_BASE_URL/LLM_API_KEY
end-to-end through a real deploy() call, not just that the env vars get
set. Delete this app + repo once that's confirmed; it's not meant to
stick around as a real platform app."""
import os

import httpx
from fastapi import FastAPI

app = FastAPI(title="zorc-ai-test-app", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/version")
async def version():
    return {"sha": os.environ.get("GIT_SHA", "dev"), "built": None}


@app.get("/openapi.json")
async def openapi_json():
    return app.openapi()


async def _call_llm(path: str, content: str):
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    if not base_url:
        return {"ok": False, "error": "LLM_BASE_URL not set -- ai: true wiring did not work"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            path,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"messages": [{"role": "user", "content": content}], "max_tokens": 300},
        )
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:200]}
    return {"ok": r.status_code == 200, "status_code": r.status_code,
            "provider": r.headers.get("x-gateway-provider"),
            "content": (body.get("choices") or [{}])[0].get("message", {}).get("content") if isinstance(body, dict) else None,
            "body": body}


@app.get("/test-ai")
async def test_ai():
    """The actual proof: reads LLM_BASE_URL/LLM_API_KEY exactly like a
    real app would (no zorc-specific knowledge, just the documented
    contract) and makes a genuine chat-completion call through them. No
    setup step beyond app.yaml's ai: true -- this must work on this
    container's very first request, no restart/warmup needed."""
    base_url = os.environ.get("LLM_BASE_URL")
    if not base_url:
        return {"ok": False, "error": "LLM_BASE_URL not set -- ai: true wiring did not work"}
    return await _call_llm(f"{base_url}/chat/completions", "reply with exactly one word: pong")


@app.get("/test-ai-batch")
async def test_ai_batch():
    """Fires several real, sequential requests through /auto -- not just
    a single lucky call -- to prove the wiring is reliably reusable
    across a container's whole lifetime, not a one-shot fluke."""
    base_url = os.environ.get("LLM_BASE_URL")
    if not base_url:
        return {"ok": False, "error": "LLM_BASE_URL not set"}
    results = []
    for i in range(5):
        results.append(await _call_llm(f"{base_url}/chat/completions", f"reply with exactly one word: pong{i}"))
    return {"all_ok": all(r["ok"] for r in results), "results": results}


@app.get("/test-ai-direct-provider")
async def test_ai_direct_provider():
    """LLM_BASE_URL only points at /auto/v1 -- but nothing stops this app
    from also reaching a SPECIFIC provider's direct route on the same
    gateway host if it actually needs one particular model, by swapping
    the path segment. Proves that still works too, not just /auto."""
    base_url = os.environ.get("LLM_BASE_URL")  # .../auto/v1
    if not base_url:
        return {"ok": False, "error": "LLM_BASE_URL not set"}
    groq_url = base_url.replace("/auto/v1", "/groq/v1")
    api_key = os.environ.get("LLM_API_KEY")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{groq_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "openai/gpt-oss-120b",
                  "messages": [{"role": "user", "content": "reply with exactly one word: pong"}],
                  "max_tokens": 300},
        )
    body = r.json()
    return {"ok": r.status_code == 200, "status_code": r.status_code,
            "content": (body.get("choices") or [{}])[0].get("message", {}).get("content")}
