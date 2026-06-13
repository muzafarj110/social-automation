"""
Analytics tests: Zernio metrics + Hub insights/viral. Both mocked.

Run:  python -m pytest backend/tests/test_analytics_flow.py -v
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


class _FakeHub:
    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def call(self, name, payload):
        return {"_log_id": 1, "summary": f"analysis for {name}",
                "recommendations": ["post more consistently"]}


class _FakeZ:
    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_analytics(self, **kw):
        return {
            "overview": {"publishedPosts": 2},
            "posts": [
                {"content": "a", "status": "published",
                 "analytics": {"impressions": 100, "likes": 5, "comments": 2},
                 "platforms": [{"platformPostUrl": "https://li/1"}]},
                {"content": "b", "status": "published",
                 "analytics": {"impressions": 50, "likes": 1, "comments": 0},
                 "platforms": [{"platformPostUrl": "https://li/2"}]},
            ],
            "hasAnalyticsAccess": True,
        }


async def _reg(c: AsyncClient, email: str, *, hub: bool = True, zernio: bool = True) -> dict:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if hub:
        await c.put("/api/auth/me/hub-key", headers=auth, json={"hub_api_key": "amh_testkey"})
    if zernio:
        await c.put("/api/auth/me/zernio-key", headers=auth, json={"zernio_api_key": "zk_testkey"})
    return auth


async def test_insights(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.analytics.HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "an_ins@b.com")
        r = await c.post("/api/analytics/insights", headers=auth,
                         json={"followers": 1000, "impressions": 20000, "post_count": 12})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["data"]["summary"] == "analysis for analytics"


async def test_viral(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.analytics.HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "an_vir@b.com")
        r = await c.post("/api/analytics/viral", headers=auth,
                         json={"post": "My best post ever", "likes": 50, "impressions": 9000})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["summary"] == "analysis for viral_analyzer"


async def test_zernio_metrics(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.analytics.ZernioClient", _FakeZ)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "an_zer@b.com")
        r = await c.get("/api/analytics/zernio", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        s = body["summary"]
        assert s["post_count"] == 2
        assert s["impressions"] == 150
        assert s["total_likes"] == 6
        assert s["avg_likes"] == 3
        assert len(s["recent"]) == 2 and s["recent"][0]["url"] == "https://li/1"


async def test_zernio_without_key_returns_friendly_empty(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.analytics.ZernioClient", _FakeZ)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "an_nokey@b.com", zernio=False)  # no Zernio key on file
        r = await c.get("/api/analytics/zernio", headers=auth)
        # No raw error — a clean signal the UI renders as a "connect an account" state.
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is False and body.get("needs_connection") is True
