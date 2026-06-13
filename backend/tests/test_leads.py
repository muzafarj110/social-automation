"""
CRM-lite: leads are owner-scoped (create/list/update/delete). Offline — no Hub
needed for CRUD (only the AI draft endpoint calls the Hub, not tested here).

Run:  python -m pytest backend/tests/test_leads.py -v
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_leads_are_owner_scoped():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        a = (await c.post("/api/auth/register", json={"email": "lead_a@b.com", "password": "supersecret"})).json()["access_token"]
        b = (await c.post("/api/auth/register", json={"email": "lead_b@b.com", "password": "supersecret"})).json()["access_token"]
        Ha, Hb = {"Authorization": f"Bearer {a}"}, {"Authorization": f"Bearer {b}"}

        lead = (await c.post("/api/leads", headers=Ha, json={"name": "Jane", "handle": "@jane"})).json()
        assert lead["status"] == "new"

        # A sees their lead; B sees none.
        assert len(((await c.get("/api/leads", headers=Ha)).json())) == 1
        assert ((await c.get("/api/leads", headers=Hb)).json()) == []

        # B can't update or delete A's lead.
        assert (await c.patch(f"/api/leads/{lead['id']}", headers=Hb, json={"status": "won"})).status_code == 404
        assert (await c.delete(f"/api/leads/{lead['id']}", headers=Hb)).status_code == 404

        # A can move it through the pipeline.
        r = await c.patch(f"/api/leads/{lead['id']}", headers=Ha, json={"status": "qualified"})
        assert r.status_code == 200 and r.json()["status"] == "qualified"
