"""
Password reset: forgot-password is enumeration-safe; reset works with a valid
token and is rejected for bad/expired/used tokens. Offline — email is disabled
(no RESEND_API_KEY), so we mint the token directly in the DB to test reset.

Run:  python -m pytest backend/tests/test_password_reset.py -v
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["JWT_SECRET"] = "test-secret-please-change"
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import init_db, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.password_reset import PasswordResetToken  # noqa: E402


async def _mint_token(email: str, raw: str, *, hours: float = 1.0) -> None:
    async with SessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == email))
        s.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
        ))
        await s.commit()


@pytest.mark.asyncio
async def test_forgot_is_enumeration_safe_and_reset_works():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.post("/api/auth/register", json={"email": "r@b.com", "password": "originalpass"})

        # forgot-password returns the SAME generic response for known + unknown emails.
        r1 = await c.post("/api/auth/forgot-password", json={"email": "r@b.com"})
        r2 = await c.post("/api/auth/forgot-password", json={"email": "nobody@b.com"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json() == r2.json()

        # A valid token resets the password and logs the user in.
        await _mint_token("r@b.com", "goodtoken123")
        r = await c.post("/api/auth/reset-password",
                         json={"token": "goodtoken123", "new_password": "brandnewpass"})
        assert r.status_code == 200 and r.json().get("access_token")

        # Old password no longer works; new one does.
        assert (await c.post("/api/auth/login", data={"username": "r@b.com", "password": "originalpass"})).status_code == 401
        assert (await c.post("/api/auth/login", data={"username": "r@b.com", "password": "brandnewpass"})).status_code == 200

        # The token is single-use now.
        assert (await c.post("/api/auth/reset-password",
                             json={"token": "goodtoken123", "new_password": "another1234"})).status_code == 400

        # A bogus token is rejected.
        assert (await c.post("/api/auth/reset-password",
                             json={"token": "doesnotexist", "new_password": "another1234"})).status_code == 400


@pytest.mark.asyncio
async def test_expired_token_rejected():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.post("/api/auth/register", json={"email": "exp@b.com", "password": "originalpass"})
        await _mint_token("exp@b.com", "expiredtoken1", hours=-1)  # already expired
        r = await c.post("/api/auth/reset-password",
                         json={"token": "expiredtoken1", "new_password": "brandnewpass"})
        assert r.status_code == 400
