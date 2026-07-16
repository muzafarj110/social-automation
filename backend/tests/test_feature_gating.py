"""
Feature gating by profile_type — ensures users only access allowed features.

Tests that:
1. Individual/Influencer can access growth_analytics, profile_optimizer, content/video tools
2. Startup/Company/Agency can access lead_gen, whatsapp_agent
3. Company (not Agency) has growth_analytics
4. Non-admin users without profile_type get 403
5. Admins bypass all checks

Run:  python -m pytest backend/tests/test_feature_gating.py -v
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
os.environ["ADMIN_EMAIL"] = "admin@example.com"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_individual_has_growth_analytics_and_profile_optimizer():
    """Individual profile should have access to growth_analytics and profile_optimizer."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        # Register user
        reg = await c.post("/api/auth/register", json={
            "email": "individual@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile type to individual
        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "individual"})

        # Check available features
        user = (await c.get("/api/auth/me", headers=headers)).json()
        features = user["available_features"]
        assert "growth_analytics" in features
        assert "profile_optimizer" in features
        assert "content_studio" in features
        assert "video_studio" in features


@pytest.mark.asyncio
async def test_influencer_has_growth_analytics():
    """Influencer profile should have access to growth_analytics."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "influencer@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "influencer"})

        user = (await c.get("/api/auth/me", headers=headers)).json()
        features = user["available_features"]
        assert "growth_analytics" in features
        assert "lead_gen" not in features  # Influencer should NOT have lead_gen


@pytest.mark.asyncio
async def test_startup_has_lead_gen_and_whatsapp():
    """Startup profile should have access to lead_gen and whatsapp_agent."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "startup@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "startup"})

        user = (await c.get("/api/auth/me", headers=headers)).json()
        features = user["available_features"]
        assert "lead_gen" in features
        assert "whatsapp_agent" in features
        assert "growth_analytics" not in features  # Startup should NOT have growth_analytics


@pytest.mark.asyncio
async def test_company_has_lead_gen_and_growth_analytics():
    """Company profile should have both lead_gen and growth_analytics."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "company@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "company"})

        user = (await c.get("/api/auth/me", headers=headers)).json()
        features = user["available_features"]
        assert "lead_gen" in features
        assert "whatsapp_agent" in features
        assert "growth_analytics" in features


@pytest.mark.asyncio
async def test_agency_has_lead_gen_no_growth_analytics():
    """Agency profile should have lead_gen/whatsapp but NOT growth_analytics."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "agency@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "agency"})

        user = (await c.get("/api/auth/me", headers=headers)).json()
        features = user["available_features"]
        assert "lead_gen" in features
        assert "whatsapp_agent" in features
        assert "growth_analytics" not in features  # Agency should NOT have growth_analytics


@pytest.mark.asyncio
async def test_lead_gen_endpoint_blocked_for_individual():
    """Individual trying to access lead_gen endpoints should get 403."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "individual_no_leads@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile to individual (no lead_gen feature)
        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "individual"})

        # Try to create a lead — should get 403
        resp = await c.post("/api/leads", headers=headers, json={
            "name": "Jane Doe",
            "handle": "@jane"
        })
        assert resp.status_code == 403
        assert "lead_gen" in resp.json()["detail"] or "not available" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_lead_gen_endpoint_allowed_for_startup():
    """Startup should be able to create leads."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "startup_leads@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile to startup (has lead_gen feature)
        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "startup"})

        # Create a lead — should succeed
        resp = await c.post("/api/leads", headers=headers, json={
            "name": "Jane Doe",
            "handle": "@jane"
        })
        assert resp.status_code == 201
        lead = resp.json()
        assert lead["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_no_profile_type_blocks_access():
    """User without profile_type set should get 403 on gated endpoints."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "no_profile@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Don't set profile_type — it's null
        # Try to create a lead — should get 403
        resp = await c.post("/api/leads", headers=headers, json={
            "name": "Jane Doe",
            "handle": "@jane"
        })
        assert resp.status_code == 403
        assert "Profile type not set" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_bypasses_feature_gating():
    """Admin user should bypass all feature gates."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        # Create admin (using admin email from config)
        reg = await c.post("/api/auth/register", json={
            "email": "admin@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Don't set any profile_type — admin should still work
        # Try to create a lead — should succeed even without profile_type
        resp = await c.post("/api/leads", headers=headers, json={
            "name": "Jane Doe",
            "handle": "@jane"
        })
        assert resp.status_code == 201
        lead = resp.json()
        assert lead["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_whatsapp_blocked_for_individual():
    """Individual trying to access WhatsApp endpoints should get 403."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "individual_no_wa@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile to individual (no whatsapp_agent feature)
        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "individual"})

        # Try to get WhatsApp agent settings — should get 403
        resp = await c.get("/api/connections/whatsapp/agent", headers=headers)
        assert resp.status_code == 403
        assert "whatsapp_agent" in resp.json()["detail"] or "not available" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_whatsapp_allowed_for_company():
    """Company should be able to access WhatsApp endpoints."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "company_wa@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile to company (has whatsapp_agent feature)
        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "company"})

        # Try to get WhatsApp agent settings — should succeed
        resp = await c.get("/api/connections/whatsapp/agent", headers=headers)
        # May return 404 if not connected, but shouldn't be 403 (permission denied)
        assert resp.status_code != 403


@pytest.mark.asyncio
async def test_list_leads_blocked_for_individual():
    """Individual trying to list leads should get 403."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        reg = await c.post("/api/auth/register", json={
            "email": "individual_list_leads@example.com",
            "password": "supersecret"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await c.put("/api/auth/me/profile", headers=headers, json={"profile_type": "individual"})

        resp = await c.get("/api/leads", headers=headers)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_lead_blocked_for_individual():
    """Individual trying to update a lead should get 403."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        # First create a startup that can create leads
        reg_startup = await c.post("/api/auth/register", json={
            "email": "startup_create@example.com",
            "password": "supersecret"
        })
        token_startup = reg_startup.json()["access_token"]
        headers_startup = {"Authorization": f"Bearer {token_startup}"}
        await c.put("/api/auth/me/profile", headers=headers_startup, json={"profile_type": "startup"})

        # Create a lead
        lead_resp = await c.post("/api/leads", headers=headers_startup, json={
            "name": "Jane Doe",
            "handle": "@jane"
        })
        lead_id = lead_resp.json()["id"]

        # Now try to update as individual
        reg_individual = await c.post("/api/auth/register", json={
            "email": "individual_update@example.com",
            "password": "supersecret"
        })
        token_individual = reg_individual.json()["access_token"]
        headers_individual = {"Authorization": f"Bearer {token_individual}"}
        await c.put("/api/auth/me/profile", headers=headers_individual, json={"profile_type": "individual"})

        # Individual can't access lead endpoints at all
        resp = await c.patch(f"/api/leads/{lead_id}", headers=headers_individual, json={"status": "qualified"})
        assert resp.status_code == 403
