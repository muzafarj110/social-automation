"""
Isolation coverage for the newer surfaces (leads CRM + billing/credits).

Confirms one customer can never read or act on another's leads (including the
AI draft-outreach action), and that credit balances are strictly per-user.
Offline — cross-tenant checks 404 before any Hub call; billing is disabled
(no Stripe) so it reports balance only. No external services needed.

Run:  python -m pytest backend/tests/test_isolation_extra.py -v
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

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


async def _reg(c: AsyncClient, email: str) -> dict:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_leads_and_credits_are_owner_scoped():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        A = await _reg(c, "iso_a@example.com")
        B = await _reg(c, "iso_b@example.com")

        # A creates a lead.
        lead = (await c.post("/api/leads", headers=A, json={"name": "Prospect"})).json()

        # B cannot see it, edit it, delete it, or AI-draft outreach on it.
        assert (await c.get("/api/leads", headers=B)).json() == []
        assert (await c.patch(f"/api/leads/{lead['id']}", headers=B, json={"status": "won"})).status_code == 404
        assert (await c.delete(f"/api/leads/{lead['id']}", headers=B)).status_code == 404
        assert (await c.post(f"/api/leads/{lead['id']}/draft-outreach", headers=B, json={})).status_code == 404

        # Credits/billing are per-user: each sees only their own balance.
        ba = (await c.get("/api/billing", headers=A)).json()
        bb = (await c.get("/api/billing", headers=B)).json()
        assert ba["credits"] == 50 and bb["credits"] == 50
        assert ba["enabled"] is False  # Stripe not configured in tests
