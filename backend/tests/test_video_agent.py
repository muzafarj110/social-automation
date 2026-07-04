"""
Video agent: channel CRUD, generate/poll/create-post flow, credits charging,
memory-first cache reuse.

The real Faceless Video Pipeline (ffmpeg/whisper/OpenRouter/Pexels) is never
invoked here — _run_pipeline_blocking is monkeypatched to a fast, deterministic
fake, and schedule_generation runs inline (awaited) instead of fire-and-forget
so tests don't need to poll/sleep for a background asyncio task.

NOTE: COST_VIDEO (15 credits) exceeds FREE_DAILY_LIMIT (5, the default free-
trial allowance) — free-trial users can never afford video generation under
current settings, since the free-trial path is gated by free_daily_limit, not
the `credits` balance. These tests use a SUBSCRIBED test user (gated by
`credits`, default 50) to exercise the real intended path. Flag this tier
mismatch to a human if free-trial access to video generation is expected.

Run:  python -m pytest backend/tests/test_video_agent.py -v
"""

from __future__ import annotations

import asyncio
import json
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
from sqlalchemy import update  # noqa: E402

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import video_generator  # noqa: E402


def _fake_outputs(tmp_path: Path) -> dict:
    """Stand-in for what run_pipeline() would return — real small files so
    shutil.move()/metadata parsing exercise the actual persist logic."""
    d = tmp_path / "fake_output"
    d.mkdir(parents=True, exist_ok=True)
    short = d / "vid_short.mp4"; short.write_bytes(b"short")
    long_ = d / "vid_long.mp4"; long_.write_bytes(b"long")
    srt_s = d / "cap_short.srt"; srt_s.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
    srt_l = d / "cap_long.srt"; srt_l.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
    thumb = d / "thumb.jpg"; thumb.write_bytes(b"jpg")
    meta = d / "meta.json"
    meta.write_text(json.dumps({
        "title": "5 Free AI Tools",
        "hashtags": ["#ai", "#tools"],
        "youtube_title": "5 Free AI Tools You Need",
        "youtube_description": "Check these out.",
        "tiktok_caption": "5 free AI tools \U0001f916",
    }))
    return {
        "video_short": short, "video_long": long_,
        "srt_short": srt_s, "srt_long": srt_l,
        "thumbnail": thumb, "metadata": meta,
    }


class FakePipeline:
    """Replaces the real (ffmpeg/whisper/network) pipeline call with a fast,
    deterministic fake. The real endpoint calls schedule_generation()
    synchronously without awaiting it (true fire-and-forget, matching
    production) — this fixture keeps that exact contract, but captures the
    created task so a test can `await fake.drain()` to await completion
    deterministically instead of sleeping/polling."""

    def __init__(self, outputs: dict) -> None:
        self.outputs = outputs
        self.tasks: list[asyncio.Task] = []

    def schedule(self, video_id: int) -> None:
        self.tasks.append(asyncio.create_task(video_generator.generate_in_background(video_id)))

    async def drain(self) -> None:
        while self.tasks:
            await self.tasks.pop()


@pytest.fixture
def fake_pipeline(monkeypatch, tmp_path):
    outputs = _fake_outputs(tmp_path)
    monkeypatch.setattr(video_generator, "_run_pipeline_blocking",
                        lambda channel_id, channel_dict, topic: outputs)
    fake = FakePipeline(outputs)
    # app/api/videos.py calls video_generator.schedule_generation(...) via the
    # module reference, so patching the attribute here is visible there too.
    monkeypatch.setattr(video_generator, "schedule_generation", fake.schedule)
    return fake


@pytest.fixture
def video_settings(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "pexels_api_key", "test-key")


async def _bootstrap_subscribed(c: AsyncClient, email: str) -> tuple[dict, int]:
    """Registers a user, links an account, and marks the user as subscribed
    so has_credits()/charge() gate on the `credits` balance (COST_VIDEO=15
    exceeds the free-trial daily allowance — see module docstring)."""
    r = await c.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    assert r.status_code == 201, r.text
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == email)
            .values(subscription_tier="pro", subscription_status="active")
        )
        await s.commit()

    r = await c.post("/api/accounts/link", headers=auth,
                     json={"zernio_account_id": "zacc_video1", "account_type": "personal"})
    assert r.status_code == 201, r.text
    return auth, r.json()["id"]


async def _create_channel(c: AsyncClient, auth: dict, **overrides) -> dict:
    body = {"name": "AIToolsDaily", "handle": "@AIToolsDaily", "niche": "AI tools", **overrides}
    r = await c.post("/api/videos/channel", headers=auth, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_generate_poll_and_create_post(fake_pipeline, video_settings):
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, account_id = await _bootstrap_subscribed(c, "video1@example.com")
        await _create_channel(c, auth)

        bill_before = (await c.get("/api/billing", headers=auth)).json()

        r = await c.post("/api/videos/generate", headers=auth, json={"topic": "5 free AI tools"})
        assert r.status_code == 202, r.text
        video = r.json()
        assert video["status"] == "queued"  # true fire-and-forget — matches production

        await fake_pipeline.drain()  # wait for the background job deterministically

        r = await c.get(f"/api/videos/jobs/{video['id']}", headers=auth)
        assert r.status_code == 200
        video = r.json()
        assert video["status"] == "completed"
        assert video["title"] == "5 Free AI Tools"
        assert video["video_short_url"] and video["video_long_url"]

        # Credit charged exactly once for the completed job.
        bill_after = (await c.get("/api/billing", headers=auth)).json()
        assert bill_before["credits"] - bill_after["credits"] == 15  # COST_VIDEO

        r = await c.get("/api/videos", headers=auth)
        assert r.status_code == 200
        assert len(r.json()) == 1

        r = await c.post(f"/api/videos/{video['id']}/create-post", headers=auth,
                         json={"account_id": account_id, "variant": "short"})
        assert r.status_code == 201, r.text
        post = r.json()
        assert post["status"] == "draft"
        assert post["media"][0]["type"] == "video"
        assert post["media"][0]["url"] == video["video_short_url"]


async def test_cache_hit_skips_regeneration_and_charge(fake_pipeline, video_settings):
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, _ = await _bootstrap_subscribed(c, "video2@example.com")
        await _create_channel(c, auth)

        r1 = await c.post("/api/videos/generate", headers=auth, json={"topic": "Same Topic"})
        assert r1.status_code == 202
        v1 = r1.json()
        await fake_pipeline.drain()

        bill_mid = (await c.get("/api/billing", headers=auth)).json()

        # Same topic, different case/whitespace — cache key normalizes both.
        r2 = await c.post("/api/videos/generate", headers=auth, json={"topic": "  same topic  "})
        assert r2.status_code == 200  # cache hit, not a new 202 job
        assert r2.json()["id"] == v1["id"]

        bill_after = (await c.get("/api/billing", headers=auth)).json()
        assert bill_mid["credits"] == bill_after["credits"]  # no second charge


async def test_generate_blocked_without_credits(fake_pipeline, video_settings):
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        auth, _ = await _bootstrap_subscribed(c, "video3@example.com")
        await _create_channel(c, auth)

        async with SessionLocal() as s:
            await s.execute(update(User).where(User.email == "video3@example.com").values(credits=0))
            await s.commit()

        r = await c.post("/api/videos/generate", headers=auth, json={"topic": "Another topic"})
        assert r.status_code == 402, r.text


async def test_generate_requires_channel_first(video_settings):
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/auth/register", json={"email": "video4@example.com", "password": "supersecret"})
        auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await c.post("/api/videos/generate", headers=auth, json={"topic": "x"})
        assert r.status_code == 404  # no channel configured yet


async def test_channel_is_one_per_user(video_settings):
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/auth/register", json={"email": "video5@example.com", "password": "supersecret"})
        auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
        await _create_channel(c, auth)

        r = await c.post("/api/videos/channel", headers=auth,
                         json={"name": "Second", "handle": "@second", "niche": "x"})
        assert r.status_code == 409  # already exists — use PATCH instead

        r = await c.patch("/api/videos/channel", headers=auth, json={"cache_duration_days": 30})
        assert r.status_code == 200
        assert r.json()["cache_duration_days"] == 30
