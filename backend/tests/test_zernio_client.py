"""
Offline tests for ZernioClient using httpx.MockTransport.
Run:  python -m pytest backend/tests/test_zernio_client.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.zernio_client import (  # noqa: E402
    ZernioAuthError,
    ZernioClient,
    ZernioDuplicateError,
    ZernioRateLimitError,
    ZernioValidationError,
)

BASE = "https://zernio.com/api/v1"
KEY = "z-key"

POST_OK = {"post": {"_id": "p1", "status": "scheduled"}, "message": "Post scheduled successfully"}


def make_client(handler) -> ZernioClient:
    ac = httpx.AsyncClient(base_url=BASE, transport=httpx.MockTransport(handler))
    return ZernioClient(BASE, KEY, max_retries=3, backoff_base=0.0, client=ac)


async def _publish_now():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json
        seen["path"] = req.url.path
        seen["auth"] = req.headers.get("Authorization")
        seen["idem"] = req.headers.get("x-request-id")
        seen["body"] = json.loads(req.content)
        return httpx.Response(201, json={"post": {"_id": "p9"}, "message": "ok"})

    z = make_client(handler)
    post = await z.publish_linkedin_now(account_id="acc1", content="Hello!", first_comment="link")
    await z.aclose()
    assert seen["path"].endswith("/posts")
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["idem"]  # auto UUID set
    p = seen["body"]["platforms"][0]
    assert p["platform"] == "linkedin" and p["accountId"] == "acc1"
    assert p["platformSpecificData"]["firstComment"] == "link"
    assert seen["body"]["publishNow"] is True
    assert post["_id"] == "p9"
    return "publish_linkedin_now: payload + bearer + idempotency"


async def _schedule():
    def handler(req: httpx.Request) -> httpx.Response:
        import json
        b = json.loads(req.content)
        assert b["scheduledFor"] == "2026-06-10T09:00:00Z"
        assert "publishNow" not in b
        return httpx.Response(201, json=POST_OK)

    z = make_client(handler)
    post = await z.schedule_linkedin(account_id="a", content="c", scheduled_for="2026-06-10T09:00:00Z")
    await z.aclose()
    assert post["status"] == "scheduled"
    return "schedule_linkedin: scheduledFor set, no publishNow"


async def _err(status, payload, exc):
    z = make_client(lambda req: httpx.Response(status, json=payload))
    raised = None
    try:
        await z.publish_linkedin_now(account_id="a", content="c")
    except Exception as e:  # noqa: BLE001
        raised = e
    await z.aclose()
    assert isinstance(raised, exc), f"{status}: got {type(raised)}"
    assert raised.status_code == status
    return f"{status} -> {exc.__name__}"


async def _dup_not_retried():
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(409, json={"error": "duplicate", "details": {"existingPostId": "x"}})

    z = make_client(handler)
    raised = None
    try:
        await z.publish_linkedin_now(account_id="a", content="c")
    except Exception as e:  # noqa: BLE001
        raised = e
    await z.aclose()
    assert isinstance(raised, ZernioDuplicateError)
    assert calls["n"] == 1, f"409 must NOT retry, got {calls['n']} calls"
    assert raised.details.get("existingPostId") == "x"
    return "409 dedup raised immediately, no retry, details preserved"


async def _retry_5xx():
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=POST_OK) if calls["n"] >= 2 else httpx.Response(502, json={"error": "bad gateway"})

    z = make_client(handler)
    post = await z.publish_linkedin_now(account_id="a", content="c")
    await z.aclose()
    assert calls["n"] == 2 and post["status"] == "scheduled"
    return "502 retried once then succeeded"


def test_publish_now():
    assert asyncio.run(_publish_now())


def test_schedule():
    assert asyncio.run(_schedule())


def test_auth():
    assert asyncio.run(_err(401, {"error": "Unauthorized"}, ZernioAuthError))


def test_validation():
    assert asyncio.run(_err(400, {"error": "platforms required"}, ZernioValidationError))


def test_rate_limit():
    assert asyncio.run(_err(429, {"error": "slow down"}, ZernioRateLimitError))


def test_dup_not_retried():
    assert asyncio.run(_dup_not_retried())


def test_retry_5xx():
    assert asyncio.run(_retry_5xx())


if __name__ == "__main__":
    async def main():
        return [
            await _publish_now(),
            await _schedule(),
            await _err(401, {"error": "Unauthorized"}, ZernioAuthError),
            await _err(400, {"error": "platforms required"}, ZernioValidationError),
            await _err(429, {"error": "slow down"}, ZernioRateLimitError),
            await _dup_not_retried(),
            await _retry_5xx(),
        ]

    out = asyncio.run(main())
    print("\n".join(f"  PASS  {r}" for r in out))
    print(f"\n{len(out)}/{len(out)} checks passed.")
