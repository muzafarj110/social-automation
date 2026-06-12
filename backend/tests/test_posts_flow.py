"""
Phase 2 tests: draft -> publish / schedule, with Zernio mocked.

Run:  python -m pytest backend/tests/test_posts_flow.py -v
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

from app.clients.zernio_client import ZernioDuplicateError  # noqa: E402
from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import publisher  # noqa: E402


class _FakeZ:
    """Stands in for ZernioClient as an async context manager."""

    def __init__(self, *, dup: bool = False) -> None:
        self.dup = dup

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def publish_linkedin_now(self, **kw):
        if self.dup:
            raise ZernioDuplicateError("dup", status_code=409,
                                       details={"existingPostId": "old"})
        return {"_id": "zp1", "platforms": [{"platformPostUrl": "https://li/p1"}]}

    async def schedule_linkedin(self, **kw):
        return {"_id": "zs1", "status": "scheduled"}


async def _bootstrap(c: AsyncClient, email: str) -> tuple[dict, int]:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    assert r.status_code == 201, r.text
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # Each user needs their own Zernio key to publish (multi-tenant isolation).
    rk = await c.put("/api/auth/me/zernio-key", headers=auth,
                     json={"zernio_api_key": "zk_usertoken"})
    assert rk.status_code == 200, rk.text
    r = await c.post("/api/accounts/link", headers=auth,
                     json={"zernio_account_id": "zacc_1", "account_type": "personal"})
    assert r.status_code == 201, r.text
    return auth, r.json()["id"]


@pytest.fixture
def zernio_key(monkeypatch):
    # Publisher now takes the key as an argument; the mock ignores it.
    monkeypatch.setattr(publisher.settings, "zernio_api_key", "zk_test")


async def test_publish_now(monkeypatch, zernio_key):
    await init_db()
    monkeypatch.setattr(publisher, "_client", lambda *a, **k: _FakeZ())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, account_id = await _bootstrap(c, "pub@b.com")
        r = await c.post("/api/posts", headers=auth,
                         json={"account_id": account_id, "body": "Hello LinkedIn!"})
        assert r.status_code == 201
        pid = r.json()["id"]
        assert r.json()["status"] == "draft"

        r = await c.post(f"/api/posts/{pid}/publish", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "published"
        assert body["zernio_post_id"] == "zp1"
        assert body["platform_post_url"] == "https://li/p1"


async def test_schedule(monkeypatch, zernio_key):
    await init_db()
    monkeypatch.setattr(publisher, "_client", lambda *a, **k: _FakeZ())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, account_id = await _bootstrap(c, "sch@b.com")
        r = await c.post("/api/posts", headers=auth,
                         json={"account_id": account_id, "body": "Scheduled post"})
        pid = r.json()["id"]
        r = await c.post(f"/api/posts/{pid}/schedule", headers=auth,
                         json={"scheduled_for": "2026-07-01T09:00:00Z", "timezone": "UTC"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "scheduled"
        assert body["zernio_post_id"] == "zs1"
        assert body["scheduled_for"].startswith("2026-07-01")


async def test_duplicate_marks_failed(monkeypatch, zernio_key):
    await init_db()
    monkeypatch.setattr(publisher, "_client", lambda *a, **k: _FakeZ(dup=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, account_id = await _bootstrap(c, "dup@b.com")
        r = await c.post("/api/posts", headers=auth,
                         json={"account_id": account_id, "body": "Dup post"})
        pid = r.json()["id"]
        r = await c.post(f"/api/posts/{pid}/publish", headers=auth)
        assert r.status_code == 409, r.text
        # post should now be FAILED with an error recorded
        r = await c.get(f"/api/posts/{pid}", headers=auth)
        assert r.json()["status"] == "failed"
        assert "Duplicate" in (r.json()["error"] or "")


async def test_ownership_isolation(monkeypatch, zernio_key):
    await init_db()
    monkeypatch.setattr(publisher, "_client", lambda *a, **k: _FakeZ())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth_a, acc_a = await _bootstrap(c, "owner_a@b.com")
        r = await c.post("/api/posts", headers=auth_a,
                         json={"account_id": acc_a, "body": "A's post"})
        pid = r.json()["id"]

        r2 = await c.post("/api/auth/register", json={"email": "owner_b@b.com", "password": "supersecret"})
        auth_b = {"Authorization": f"Bearer {r2.json()['access_token']}"}
        # B cannot see or publish A's post
        assert (await c.get(f"/api/posts/{pid}", headers=auth_b)).status_code == 404
        assert (await c.post(f"/api/posts/{pid}/publish", headers=auth_b)).status_code == 404


async def test_publish_without_zernio_key_blocked(monkeypatch, zernio_key):
    """A user with no Zernio key on file cannot publish (isolation gate)."""
    await init_db()
    monkeypatch.setattr(publisher, "_client", lambda *a, **k: _FakeZ())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/auth/register",
                         json={"email": "nokey@b.com", "password": "supersecret"})
        auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await c.post("/api/accounts/link", headers=auth,
                         json={"zernio_account_id": "zacc_x", "account_type": "personal"})
        acc = r.json()["id"]
        r = await c.post("/api/posts", headers=auth,
                         json={"account_id": acc, "body": "no key post"})
        pid = r.json()["id"]
        r = await c.post(f"/api/posts/{pid}/publish", headers=auth)
        assert r.status_code == 400, r.text
