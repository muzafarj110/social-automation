"""
Usage-based credits: generation spends credits and blocks at zero.

Hub is mocked so no external service is needed. Billing endpoints report
'disabled' when Stripe isn't configured (the default in tests).

Run:  python -m pytest backend/tests/test_credits.py -v
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
os.environ["ADMIN_EMAIL"] = "nobody-admin@example.com"
os.environ["FREE_CREDITS"] = "50"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.api import content as content_api  # noqa: E402
from app.models.user import User  # noqa: E402
from sqlalchemy import update  # noqa: E402


class _FakeHub:
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *e): return False
    async def generate_text_post(self, **kw):
        return {"full_post": "hello world", "hashtags": ["#hi"]}


@pytest.mark.asyncio
async def test_generation_spends_credits_and_blocks_at_zero(monkeypatch):
    await init_db()
    monkeypatch.setattr(content_api, "HubClient", _FakeHub)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        tok = (await c.post("/api/auth/register", json={
            "email": "credit@example.com", "password": "supersecret"})).json()["access_token"]
        H = {"Authorization": f"Bearer {tok}"}

        # Billing shows disabled (no Stripe) but a starting balance.
        bill = (await c.get("/api/billing", headers=H)).json()
        assert bill["enabled"] is False and bill["credits"] == 50

        # A generation succeeds and decrements the balance.
        r = await c.post("/api/content/generate/post", headers=H, json={"topic": "x"})
        assert r.status_code == 200, r.text
        assert r.json()["credits"] == 49

        # Drain to zero, then the next generation is blocked with 402.
        async with SessionLocal() as s:
            await s.execute(update(User).where(User.email == "credit@example.com").values(credits=0))
            await s.commit()
        r = await c.post("/api/content/generate/post", headers=H, json={"topic": "y"})
        assert r.status_code == 402, r.text
