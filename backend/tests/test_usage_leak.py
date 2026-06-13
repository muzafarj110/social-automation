"""
Regression tests for the Hub-key leak + media-platform guard.

The leak: a user WITHOUT their own Hub key falls back to the shared server key.
/api/content/usage must NOT call the Hub or expose the shared key owner's
account (email, plan, referral code). It must return a generic managed payload.
This runs fully offline (managed path makes no network call).

Run:  python -m pytest backend/tests/test_usage_leak.py -v
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
# Give the app a shared/server Hub key (the owner's). If the endpoint leaked,
# it would try to use this to fetch the owner's /api/me.
os.environ["HUB_API_KEY"] = "amh_shared_owner_key_should_never_be_exposed"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import publisher  # noqa: E402
from app.models.post import Post  # noqa: E402


@pytest.mark.asyncio
async def test_usage_does_not_leak_owner_account_for_keyless_user():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/auth/register", json={
            "email": "keyless@example.com", "password": "supersecret"})
        token = r.json()["access_token"]

        r = await c.get("/api/content/usage", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        body = r.json()

        # Managed path: flagged managed, and NO owner identity anywhere.
        assert body.get("managed") is True
        blob = str(body).lower()
        for leaked in ["email", "@", "referral", "owner", "amh_"]:
            assert leaked not in blob, f"usage payload leaked '{leaked}': {body}"


def test_media_required_platforms_blocked_without_media():
    p = Post()
    p.id = 1
    p.body = "text only"
    p.hashtags = None
    p.media = None
    p.first_comment = None
    # text-only platforms are fine
    assert publisher.needs_media(p, "linkedin") is False
    assert publisher.needs_media(p, "twitter") is False
    # media-first platforms must be flagged
    for plat in ["instagram", "tiktok", "youtube", "pinterest", "snapchat"]:
        assert publisher.needs_media(p, plat) is True, plat
    # once media is attached, they're allowed
    p.media = [{"type": "image", "url": "https://x/y.jpg"}]
    assert publisher.needs_media(p, "instagram") is False
