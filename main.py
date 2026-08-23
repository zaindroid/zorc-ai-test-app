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


@app.get("/test-ai")
async def test_ai():
    """The actual proof: reads LLM_BASE_URL/LLM_API_KEY exactly like a
    real app would (no zorc-specific knowledge, just the documented
    contract) and makes a genuine chat-completion call through them."""
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    if not base_url:
        return {"ok": False, "error": "LLM_BASE_URL not set -- ai: true wiring did not work"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"messages": [{"role": "user", "content": "reply with exactly one word: pong"}],
                  "max_tokens": 300},
        )
    return {"ok": r.status_code == 200, "status_code": r.status_code,
            "provider": r.headers.get("x-gateway-provider"), "body": r.json()}
