"""
Free-tier limits: Autopilot is available but capped (1 campaign, ≤3 posts/week).
Offline — linking an account and creating a campaign are pure DB writes.

Run:  python -m pytest backend/tests/test_plan_limits.py -v
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
async def test_free_plan_gets_autopilot_but_capped():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/auth/register", json={
            "email": "free@example.com", "password": "supersecret"})
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}

        # Free plan now includes autopilot.
        me = (await c.get("/api/auth/me", headers=H)).json()
        assert me["plan"] == "free"
        assert me["entitlements"]["autopilot"] is True

        # Link an account (pure DB write).
        acc = (await c.post("/api/accounts/link", headers=H, json={
            "zernio_account_id": "acc_free", "platform": "linkedin"})).json()

        # First campaign with a high cadence — allowed, but clamped to the cap.
        r1 = await c.post("/api/campaigns", headers=H, json={
            "name": "C1", "account_id": acc["id"], "topics": ["x"],
            "frequency_per_week": 10})
        assert r1.status_code == 201, r1.text
        assert r1.json()["frequency_per_week"] == 3  # clamped to free cap

        # Second campaign — blocked by the free cap.
        r2 = await c.post("/api/campaigns", headers=H, json={
            "name": "C2", "account_id": acc["id"], "topics": ["y"]})
        assert r2.status_code == 402, r2.text
