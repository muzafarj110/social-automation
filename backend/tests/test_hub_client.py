"""
Offline tests for HubClient using httpx.MockTransport — no real key needed.
Run:  python -m pytest backend/tests/test_hub_client.py -v
  or: python backend/tests/test_hub_client.py   (runs a built-in runner)
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

# Make `app` importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.hub_client import (  # noqa: E402
    HubAuthError,
    HubClient,
    HubPermissionError,
    HubRateLimitError,
    HubServerError,
    HubValidationError,
)

BASE = "https://hub.example.com"
KEY = "test-key"

SUCCESS_BODY = {
    "success": True,
    "log_id": 142,
    "data": {
        "hook": "I almost quit my startup after 6 months.",
        "full_post": "I almost quit my startup after 6 months.\n\n...",
        "character_count": 1087,
        "post_type": "Personal Story + Lesson",
        "hashtags": ["#startups", "#entrepreneurship", "#founders"],
        "cta_line": "What kept you going when you wanted to quit?",
    },
}


def make_client(handler) -> HubClient:
    transport = httpx.MockTransport(handler)
    ac = httpx.AsyncClient(base_url=BASE, transport=transport)
    # max_retries small + zero backoff to keep tests fast
    return HubClient(BASE, KEY, max_retries=3, backoff_base=0.0, client=ac)


async def _run_success():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["api_key"] = request.headers.get("X-API-Key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=SUCCESS_BODY)

    hub = make_client(handler)
    data = await hub.generate_text_post(
        topic="quitting my startup",
        post_type="Personal Story + Lesson",
        audience="early-stage founders",
        tone="professional but human",
        include_cta="question to comments",
    )
    await hub.aclose()
    assert seen["path"] == "/api/linkedin-text-post", seen["path"]
    assert seen["api_key"] == KEY
    assert seen["body"]["include_cta"] == "question to comments"
    assert data["character_count"] == 1087
    assert data["_log_id"] == 142
    return "success envelope parsed + auth header sent"


async def _run_error(status: int, detail: str, exc_type):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": detail})

    hub = make_client(handler)
    raised = None
    try:
        await hub.generate_text_post(
            topic="t", post_type="p", audience="a", tone="x"
        )
    except Exception as e:  # noqa: BLE001
        raised = e
    await hub.aclose()
    assert isinstance(raised, exc_type), f"expected {exc_type}, got {type(raised)}"
    assert raised.status_code == status
    assert detail in raised.message
    return f"{status} -> {exc_type.__name__}"


async def _run_retry_then_success():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"detail": "upstream down"})
        return httpx.Response(200, json=SUCCESS_BODY)

    hub = make_client(handler)
    data = await hub.generate_text_post(
        topic="t", post_type="p", audience="a", tone="x"
    )
    await hub.aclose()
    assert calls["n"] == 3, calls["n"]
    assert data["character_count"] == 1087
    return "retried 5xx twice then succeeded"


async def _run_retry_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "Rate limit exceeded."})

    hub = make_client(handler)
    raised = None
    try:
        await hub.generate_text_post(topic="t", post_type="p", audience="a", tone="x")
    except Exception as e:  # noqa: BLE001
        raised = e
    await hub.aclose()
    assert isinstance(raised, HubRateLimitError), type(raised)
    return "429 retried to exhaustion -> HubRateLimitError"


async def _run_generic_call():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/linkedin-comment-writer"
        return httpx.Response(200, json={"success": True, "log_id": 9, "data": {"draft": "Nice!"}})

    hub = make_client(handler)
    data = await hub.write_comment(post_url="https://x", angle="supportive")
    await hub.aclose()
    assert data["draft"] == "Nice!"
    return "generic passthrough (comment_writer) works"


# pytest-style test functions ------------------------------------------------
def test_success():
    assert asyncio.run(_run_success())


def test_auth_error():
    assert asyncio.run(_run_error(401, "API key required.", HubAuthError))


def test_validation_error():
    assert asyncio.run(_run_error(400, "Topic cannot be empty", HubValidationError))


def test_permission_error():
    assert asyncio.run(_run_error(403, "Model not available on your plan.", HubPermissionError))


def test_server_error():
    assert asyncio.run(_run_error(500, "boom", HubServerError))


def test_retry_then_success():
    assert asyncio.run(_run_retry_then_success())


def test_retry_exhausted():
    assert asyncio.run(_run_retry_exhausted())


def test_generic_call():
    assert asyncio.run(_run_generic_call())


# Standalone runner (no pytest required) -------------------------------------
if __name__ == "__main__":
    checks = [
        _run_success(),
        _run_error(401, "API key required.", HubAuthError),
        _run_error(400, "Topic cannot be empty", HubValidationError),
        _run_error(403, "Model not available on your plan.", HubPermissionError),
        _run_error(500, "boom", HubServerError),
        _run_retry_then_success(),
        _run_retry_exhausted(),
        _run_generic_call(),
    ]

    async def main():
        results = []
        for c in checks:
            results.append(await c)
        return results

    out = asyncio.run(main())
    print("\n".join(f"  PASS  {r}" for r in out))
    print(f"\n{len(out)}/{len(out)} checks passed.")
