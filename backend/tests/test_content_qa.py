"""
Content quality tools: QA, optimize, infographic, usage. Hub mocked.

Run:  python -m pytest backend/tests/test_content_qa.py -v
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
        if name == "score_checker":
            return {"score": 88, "verdict": "strong"}
        if name == "content_optimizer":
            return {"optimized_content": "An improved version of the post."}
        return {"name": name, "summary": f"{name} output"}

    async def get_raw(self, path):
        return {"plan": "free", "calls_used": 12, "limit": 50}


async def _reg(c: AsyncClient, email: str) -> dict:
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
    await c.put("/api/auth/me/hub-key", headers=auth, json={"hub_api_key": "amh_testkey"})
    return auth


async def test_qa_check(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.content.HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "qa_a@b.com")
        r = await c.post("/api/content/qa", headers=auth,
                         json={"content": "Here is my LinkedIn post.", "topic": "AI"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["score"]["score"] == 88
        assert body["qa"]["summary"] == "qa output"
        assert body["ai_detection"]["summary"] == "ai_detector output"


async def test_optimize(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.content.HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "qa_opt@b.com")
        r = await c.post("/api/content/optimize", headers=auth,
                         json={"content": "rough draft"})
        assert r.status_code == 200, r.text
        assert "improved" in r.json()["data"]["optimized_content"].lower()


async def test_infographic_and_usage(monkeypatch):
    await init_db()
    monkeypatch.setattr("app.api.content.HubClient", _FakeHub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth = await _reg(c, "qa_info@b.com")
        r = await c.post("/api/content/infographic", headers=auth,
                         json={"topic": "AI trends", "content_points": "a; b; c"})
        assert r.status_code == 200 and r.json()["ok"] is True

        r = await c.get("/api/content/usage", headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["plan"] == "free"
        assert r.json()["data"]["calls_used"] == 12
