"""
Multi-tenant isolation — proves user A can never see or act on user B's data.

This closes the class of bug we hit early on ("I can see all accounts connected
to another user"). Runs against the real ASGI app on a throwaway SQLite DB; no
external services are called (linking an account is a pure DB write, and the
ownership checks run before any Zernio/Hub call).

Run:  python -m pytest backend/tests/test_isolation.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["JWT_SECRET"] = "test-secret-please-change"
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")
# Make sure neither test user is the admin (admin bypasses entitlements).
os.environ["ADMIN_EMAIL"] = "nobody-admin@example.com"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


async def _register(c: AsyncClient, email: str) -> str:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_users_cannot_see_or_touch_each_others_data():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        a = await _register(c, "alice@example.com")
        b = await _register(c, "bob@example.com")

        # Alice links a LinkedIn account and a Twitter account.
        r = await c.post("/api/accounts/link", headers=_auth(a), json={
            "zernio_account_id": "acc_alice_li", "platform": "linkedin",
            "display_name": "Alice LI"})
        assert r.status_code == 201, r.text
        alice_acc = r.json()
        assert alice_acc["platform"] == "linkedin"

        r = await c.post("/api/accounts/link", headers=_auth(a), json={
            "zernio_account_id": "acc_alice_x", "platform": "twitter",
            "display_name": "Alice X"})
        assert r.status_code == 201

        # Bob links his own account.
        r = await c.post("/api/accounts/link", headers=_auth(b), json={
            "zernio_account_id": "acc_bob_li", "platform": "linkedin",
            "display_name": "Bob LI"})
        assert r.status_code == 201
        bob_acc = r.json()

        # Each user sees ONLY their own accounts.
        ra = await c.get("/api/accounts", headers=_auth(a))
        rb = await c.get("/api/accounts", headers=_auth(b))
        a_ids = {x["zernio_account_id"] for x in ra.json()}
        b_ids = {x["zernio_account_id"] for x in rb.json()}
        assert a_ids == {"acc_alice_li", "acc_alice_x"}
        assert b_ids == {"acc_bob_li"}
        assert a_ids.isdisjoint(b_ids)

        # Bob cannot unlink Alice's account.
        r = await c.delete(f"/api/accounts/{alice_acc['id']}", headers=_auth(b))
        assert r.status_code == 404

        # Alice creates a post; Bob cannot read, edit, publish, schedule or delete it.
        r = await c.post("/api/posts", headers=_auth(a), json={
            "account_id": alice_acc["id"], "body": "Alice's private draft"})
        assert r.status_code == 201, r.text
        post = r.json()
        assert post["platform"] == "linkedin"

        for method, path in [
            ("get", f"/api/posts/{post['id']}"),
            ("patch", f"/api/posts/{post['id']}"),
            ("delete", f"/api/posts/{post['id']}"),
            ("post", f"/api/posts/{post['id']}/publish"),
            ("post", f"/api/posts/{post['id']}/schedule"),
        ]:
            kwargs = {"headers": _auth(b)}
            if method == "patch":
                kwargs["json"] = {"body": "hijacked"}
            if path.endswith("/schedule"):
                kwargs["json"] = {"scheduled_for": "2030-01-01T00:00:00Z"}
            r = await getattr(c, method)(path, **kwargs)
            assert r.status_code == 404, f"{method} {path} leaked: {r.status_code}"

        # Bob cannot create a post against Alice's account.
        r = await c.post("/api/posts", headers=_auth(b), json={
            "account_id": alice_acc["id"], "body": "trying to use Alice's account"})
        assert r.status_code == 404

        # Bob cannot point a campaign at Alice's account.
        r = await c.post("/api/campaigns", headers=_auth(b), json={
            "name": "x", "account_id": alice_acc["id"], "topics": ["hi"]})
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_campaign_actions_are_owner_only():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        a = await _register(c, "carol@example.com")
        b = await _register(c, "dave@example.com")

        r = await c.post("/api/accounts/link", headers=_auth(a), json={
            "zernio_account_id": "acc_carol", "platform": "linkedin"})
        acc = r.json()
        r = await c.post("/api/campaigns", headers=_auth(a), json={
            "name": "Carol weekly", "account_id": acc["id"],
            "platforms": ["linkedin", "twitter"], "topics": ["leadership"]})
        assert r.status_code == 201, r.text
        camp = r.json()
        assert camp["platforms"] == ["linkedin", "twitter"]

        # Dave can't see, modify, run or delete Carol's campaign.
        assert (await c.patch(f"/api/campaigns/{camp['id']}", headers=_auth(b),
                              json={"name": "stolen"})).status_code == 404
        assert (await c.post(f"/api/campaigns/{camp['id']}/run",
                             headers=_auth(b))).status_code == 404
        assert (await c.delete(f"/api/campaigns/{camp['id']}",
                               headers=_auth(b))).status_code == 404
        # Dave's own campaign list is empty.
        assert (await c.get("/api/campaigns", headers=_auth(b))).json() == []


@pytest.mark.asyncio
async def test_admin_endpoints_reject_non_admin():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _register(c, "regular@example.com")
        assert (await c.get("/api/admin/users", headers=_auth(token))).status_code == 403
        assert (await c.get("/api/admin/features", headers=_auth(token))).status_code == 403
        assert (await c.patch("/api/admin/users/1", headers=_auth(token),
                              json={"plan": "pro"})).status_code == 403
