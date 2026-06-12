"""
Autopilot campaign tests: create -> run, in both approve and auto modes.
Hub and Zernio are mocked, so no external services are needed.

Run:  python -m pytest backend/tests/test_campaigns_flow.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmp.name}")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import campaigns as svc  # noqa: E402
from app.services import publisher  # noqa: E402


class _FakeHub:
    """Stands in for HubClient as an async context manager."""

    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def generate_text_post(self, *, topic, **kw):
        return {"full_post": f"A post about {topic}", "hashtags": ["#growth"]}

    async def call(self, name, payload):
        return {}  # goal-mode calendar -> empty, orchestrator falls back


class _FakeZ:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def schedule_linkedin(self, **kw):
        return {"_id": "zs1", "status": "scheduled"}


async def _bootstrap(c: AsyncClient, email: str, *, zernio: bool = True) -> int:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
    await c.put("/api/auth/me/hub-key", headers=auth, json={"hub_api_key": "amh_testkey"})
    if zernio:
        await c.put("/api/auth/me/zernio-key", headers=auth, json={"zernio_api_key": "zk_testkey"})
    r = await c.post("/api/accounts/link", headers=auth,
                     json={"zernio_account_id": "zacc_1", "account_type": "personal"})
    return auth, r.json()["id"]


_BASE = {
    "frequency_per_week": 3,
    "days": [0, 1, 2, 3, 4, 5, 6],
    "time_of_day": "23:00",
    "timezone": "UTC",
    "topic_source": "topics",
    "topics": ["Scaling lessons", "Why marketing fails", "AI tools I use"],
}


async def test_create_and_run_approve_mode(monkeypatch):
    await init_db()
    monkeypatch.setattr(svc, "HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, acc = await _bootstrap(c, "camp_a@b.com")
        r = await c.post("/api/campaigns", headers=auth,
                         json={"name": "Weekly", "account_id": acc, "mode": "approve", **_BASE})
        assert r.status_code == 201, r.text
        cid = r.json()["id"]
        assert r.json()["status"] == "active"

        r = await c.post(f"/api/campaigns/{cid}/run", headers=auth)
        assert r.status_code == 200, r.text
        posts = r.json()
        assert len(posts) == 3
        for p in posts:
            assert p["status"] == "draft"          # approve mode = drafts
            assert p["source"] == "generated"
            assert p["scheduled_for"] is not None   # suggested slot
            assert p["hashtags"] == ["#growth"]

        # the drafts show up in the posts list
        r = await c.get("/api/posts", headers=auth)
        assert len([p for p in r.json() if p["source"] == "generated"]) == 3


async def test_run_auto_mode_schedules(monkeypatch):
    await init_db()
    monkeypatch.setattr(svc, "HubClient", _FakeHub)
    monkeypatch.setattr(publisher, "_client", lambda *a, **k: _FakeZ())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, acc = await _bootstrap(c, "camp_b@b.com")
        r = await c.post("/api/campaigns", headers=auth,
                         json={"name": "Auto", "account_id": acc, "mode": "auto", **_BASE})
        cid = r.json()["id"]
        r = await c.post(f"/api/campaigns/{cid}/run", headers=auth)
        assert r.status_code == 200, r.text
        posts = r.json()
        assert len(posts) == 3
        for p in posts:
            assert p["status"] == "scheduled"
            assert p["zernio_post_id"] == "zs1"


async def test_auto_mode_requires_zernio_key(monkeypatch):
    await init_db()
    monkeypatch.setattr(svc, "HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, acc = await _bootstrap(c, "camp_c@b.com", zernio=False)
        r = await c.post("/api/campaigns", headers=auth,
                         json={"name": "NoKey", "account_id": acc, "mode": "auto", **_BASE})
        cid = r.json()["id"]
        r = await c.post(f"/api/campaigns/{cid}/run", headers=auth)
        assert r.status_code == 400, r.text


async def test_update_pause_and_ownership(monkeypatch):
    await init_db()
    monkeypatch.setattr(svc, "HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth_a, acc = await _bootstrap(c, "camp_owner_a@b.com")
        r = await c.post("/api/campaigns", headers=auth_a,
                         json={"name": "Mine", "account_id": acc, "mode": "approve", **_BASE})
        cid = r.json()["id"]

        r = await c.patch(f"/api/campaigns/{cid}", headers=auth_a, json={"status": "paused"})
        assert r.status_code == 200 and r.json()["status"] == "paused"

        r2 = await c.post("/api/auth/register",
                          json={"email": "camp_owner_b@b.com", "password": "supersecret"})
        auth_b = {"Authorization": f"Bearer {r2.json()['access_token']}"}
        assert (await c.get(f"/api/campaigns/{cid}", headers=auth_b)).status_code == 404
        assert (await c.post(f"/api/campaigns/{cid}/run", headers=auth_b)).status_code == 404
