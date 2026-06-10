"""
End-to-end auth + account flow against the real ASGI app, on a throwaway
SQLite DB. No external services needed.

Run:  python -m pytest backend/tests/test_auth_flow.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Configure a temp DB + secret BEFORE importing the app/config.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["JWT_SECRET"] = "test-secret-please-change"
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_register_login_me_and_accounts():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # register
        r = await c.post("/api/auth/register", json={
            "email": "a@b.com", "password": "supersecret", "full_name": "Mr J"})
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        assert token

        # duplicate register -> 409
        r = await c.post("/api/auth/register", json={
            "email": "a@b.com", "password": "supersecret"})
        assert r.status_code == 409

        # login (OAuth2 form)
        r = await c.post("/api/auth/login", data={
            "username": "a@b.com", "password": "supersecret"})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]

        auth = {"Authorization": f"Bearer {token}"}

        # me
        r = await c.get("/api/auth/me", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "a@b.com" and body["has_hub_key"] is False

        # protected route without token -> 401
        r = await c.get("/api/accounts")
        assert r.status_code == 401

        # set hub key (encrypted at rest)
        r = await c.put("/api/auth/me/hub-key", headers=auth,
                        json={"hub_api_key": "amh_testkey123"})
        assert r.status_code == 200 and r.json()["has_hub_key"] is True

        # link a LinkedIn account
        r = await c.post("/api/accounts/link", headers=auth, json={
            "zernio_account_id": "zacc_123", "account_type": "personal",
            "display_name": "Mr J"})
        assert r.status_code == 201, r.text
        acc_id = r.json()["id"]

        # duplicate link -> 409
        r = await c.post("/api/accounts/link", headers=auth, json={
            "zernio_account_id": "zacc_123"})
        assert r.status_code == 409

        # list
        r = await c.get("/api/accounts", headers=auth)
        assert r.status_code == 200 and len(r.json()) == 1

        # unlink
        r = await c.delete(f"/api/accounts/{acc_id}", headers=auth)
        assert r.status_code == 204

        r = await c.get("/api/accounts", headers=auth)
        assert r.json() == []


def test_password_and_token_helpers():
    from app.core.security import (
        create_access_token,
        decode_access_token,
        encrypt_secret,
        decrypt_secret,
        hash_password,
        verify_password,
    )

    h = hash_password("hunter2!!")
    assert verify_password("hunter2!!", h)
    assert not verify_password("wrong", h)

    tok = create_access_token(42)
    assert decode_access_token(tok)["sub"] == "42"

    enc = encrypt_secret("amh_secretkey")
    assert enc != "amh_secretkey"
    assert decrypt_secret(enc) == "amh_secretkey"
