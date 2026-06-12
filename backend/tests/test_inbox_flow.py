"""
Phase 4 tests: approval inbox. Hub drafting and Zernio execution are mocked,
so no external services or keys are needed.

Run:  python -m pytest backend/tests/test_inbox_flow.py -v
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
from app.services import approvals as svc  # noqa: E402


def _mock_hub(monkeypatch, text="Drafted reply ✦", payload=None):
    async def fake_generate(user, kind, params):
        return (payload or {"message": text, "_log_id": 1}, text)

    monkeypatch.setattr(svc, "generate_draft", fake_generate)


async def _register(c: AsyncClient, email: str) -> dict:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- unit: draft-text extraction ------------------------------------------
def test_extract_draft_text_variants():
    assert svc.extract_draft_text("comment", {"comment": "nice point!"}) == "nice point!"
    assert svc.extract_draft_text("dm", {"message": "hey there"}) == "hey there"
    # outreach: list of step dicts -> first message
    assert svc.extract_draft_text(
        "outreach", {"steps": [{"message": "step one"}, {"message": "step two"}]}
    ) == "step one"
    # fallback: first non-underscore string value
    assert svc.extract_draft_text("profile", {"_log_id": 9, "headline": "Builder"}) == "Builder"


# --- flow: generate -> edit -> approve (manual) ---------------------------
async def test_generate_edit_approve_manual(monkeypatch):
    await init_db()
    _mock_hub(monkeypatch, text="Original DM draft")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _register(c, "inbox_a@b.com")

        r = await c.post("/api/inbox/generate", headers=auth,
                         json={"kind": "dm", "params": {"recipient_name": "Jane"}})
        assert r.status_code == 201, r.text
        item = r.json()
        assert item["status"] == "pending"
        assert item["draft_text"] == "Original DM draft"
        aid = item["id"]

        # appears in the pending list
        r = await c.get("/api/inbox", headers=auth)
        assert r.status_code == 200 and len(r.json()) == 1

        # edit the draft
        r = await c.patch(f"/api/inbox/{aid}", headers=auth,
                          json={"draft_text": "Edited DM draft"})
        assert r.status_code == 200 and r.json()["draft_text"] == "Edited DM draft"

        # approve -> manual (no official API for DMs)
        r = await c.post(f"/api/inbox/{aid}/approve", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "approved"
        assert body["executed_via"] == "manual"
        assert body["resolved_at"] is not None

        # no longer pending
        assert len(((await c.get("/api/inbox", headers=auth)).json())) == 0
        assert len(((await c.get("/api/inbox?status=approved", headers=auth)).json())) == 1


# --- flow: company-page comment executes via Zernio -----------------------
async def test_comment_company_reply_via_zernio(monkeypatch):
    await init_db()
    _mock_hub(monkeypatch, text="Thanks for the kind words!")
    calls = {}

    async def fake_reply(comment_id, message, *, zernio_key=None):
        calls["comment_id"] = comment_id
        calls["message"] = message
        return {"id": "reply_1"}

    monkeypatch.setattr(svc, "reply_company_comment", fake_reply)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _register(c, "inbox_b@b.com")
        r = await c.post("/api/inbox/generate", headers=auth, json={
            "kind": "comment",
            "params": {"post_url": "https://li/post/1", "angle": "supportive"},
            "context": {"comment_id": "cmt_42", "post_url": "https://li/post/1"},
        })
        aid = r.json()["id"]

        r = await c.post(f"/api/inbox/{aid}/approve", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "sent"
        assert body["executed_via"] == "zernio"
        assert calls == {"comment_id": "cmt_42", "message": "Thanks for the kind words!"}


# --- flow: personal comment (no comment_id) stays manual ------------------
async def test_personal_comment_is_manual(monkeypatch):
    await init_db()
    _mock_hub(monkeypatch, text="Great post — adding a thought.")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _register(c, "inbox_c@b.com")
        r = await c.post("/api/inbox/generate", headers=auth, json={
            "kind": "comment",
            "params": {"post_url": "https://li/post/2"},
            "context": {"post_url": "https://li/post/2"},  # no comment_id
        })
        aid = r.json()["id"]
        r = await c.post(f"/api/inbox/{aid}/approve", headers=auth)
        assert r.json()["status"] == "approved" and r.json()["executed_via"] == "manual"


# --- reject + ownership isolation -----------------------------------------
async def test_reject_and_ownership(monkeypatch):
    await init_db()
    _mock_hub(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth_a = await _register(c, "inbox_owner_a@b.com")
        r = await c.post("/api/inbox/generate", headers=auth_a,
                         json={"kind": "dm", "params": {}})
        aid = r.json()["id"]

        # reject
        r = await c.post(f"/api/inbox/{aid}/reject", headers=auth_a)
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        # a rejected item cannot be approved
        assert (await c.post(f"/api/inbox/{aid}/approve", headers=auth_a)).status_code == 409

        # another user cannot see or act on it
        auth_b = await _register(c, "inbox_owner_b@b.com")
        assert (await c.get(f"/api/inbox/{aid}", headers=auth_b)).status_code == 404
        assert (await c.post(f"/api/inbox/{aid}/approve", headers=auth_b)).status_code == 404
