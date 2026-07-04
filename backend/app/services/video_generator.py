"""
Video agent — bridge between FastAPI and the vendored Faceless Video Pipeline.

The vendored pipeline (app/vendor/faceless_pipeline) is a synchronous,
blocking, standalone-script-style tool (FFmpeg subprocess calls, Whisper
transcription, HTTP calls to Pexels/OpenRouter) with no async awareness. This
module:
  1. Bridges a VideoChannel DB row to the on-disk channels/<slug>.yaml file
     the vendored config.py expects (config.load_channel()).
  2. Runs the blocking pipeline call in a thread pool so it never blocks the
     FastAPI event loop — a ~3 minute job would otherwise stall every other
     request on this single-process Railway deploy.
  3. Moves the pipeline's output files into the app's own UPLOAD_DIR and
     builds public URLs, matching the existing media.py upload convention.
  4. Implements the "memory-first" cache lookup: reuse a completed video for
     the same channel+topic within its configured cache window instead of
     regenerating.

Generation continues after the HTTP response has already been returned to the
client, so it owns an independent DB session (not the request's) — see
generate_in_background().
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core import credits
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.generated_video import COMPLETED, FAILED, GENERATING, GeneratedVideo
from app.models.user import User
from app.models.video_channel import VideoChannel

log = logging.getLogger("uvicorn.error")

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "faceless_pipeline"
# Bounds concurrent FFmpeg/Whisper jobs so a burst of requests doesn't starve
# the single web dyno's CPU. Starting guess — tune after observing real load.
_EXECUTOR = ThreadPoolExecutor(max_workers=2)
# Holds references to fire-and-forget background tasks so they aren't
# garbage-collected mid-run (a well-known asyncio gotcha).
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _channel_slug(channel_id: int) -> str:
    return f"video_channel_{channel_id}"


def topic_cache_key(channel_id: int, topic: str) -> str:
    normalized = topic.strip().lower()
    return hashlib.sha256(f"{channel_id}:{normalized}".encode()).hexdigest()


def _write_channel_yaml(channel_id: int, channel_dict: dict) -> str:
    """Serialize a plain dict (read from the DB row before crossing into a
    worker thread) into the exact YAML schema config.load_channel() expects.
    Returns the channel slug used to call run_pipeline()."""
    import yaml
    slug = _channel_slug(channel_id)
    channels_dir = VENDOR_ROOT / "channels"
    channels_dir.mkdir(parents=True, exist_ok=True)
    (channels_dir / f"{slug}.yaml").write_text(yaml.safe_dump(channel_dict))
    return slug


def _run_pipeline_blocking(channel_id: int, channel_dict: dict, topic: str) -> dict:
    """Runs on a worker thread — imports the vendored main.py and calls
    run_pipeline() unmodified. Pure function of (channel, topic) -> output
    file paths; takes no DB session (async sessions aren't thread-safe)."""
    if str(VENDOR_ROOT) not in sys.path:
        sys.path.insert(0, str(VENDOR_ROOT))
    import main as pipeline_main  # the vendored main.py — see module docstring
    slug = _write_channel_yaml(channel_id, channel_dict)
    return pipeline_main.run_pipeline(
        channel_name=slug, topic=topic, mode="both",
        script_file=None, keep_temp=False,
    )


async def find_cached(db, channel: VideoChannel, topic: str) -> GeneratedVideo | None:
    """Memory-first: reuse a completed video for the same channel+topic if one
    exists within the channel's configured cache window, instead of paying
    for a fresh script/footage/render/transcription run."""
    cache_key = topic_cache_key(channel.id, topic)
    cutoff = datetime.now(timezone.utc) - timedelta(days=channel.cache_duration_days)
    return await db.scalar(
        select(GeneratedVideo)
        .where(
            GeneratedVideo.channel_id == channel.id,
            GeneratedVideo.topic_cache_key == cache_key,
            GeneratedVideo.status == COMPLETED,
            GeneratedVideo.completed_at >= cutoff,
        )
        .order_by(GeneratedVideo.completed_at.desc())
    )


def _persist_outputs(video: GeneratedVideo, outputs: dict, user_id: int) -> None:
    """Move the pipeline's output files into settings.upload_dir and build
    public URLs, matching the existing media.py upload convention. Moves
    (not copies) to avoid doubling disk usage on Railway's ephemeral disk."""
    dest_dir = Path(settings.upload_dir) / "videos" / str(user_id) / str(video.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    base = (settings.app_base_url or "").rstrip("/")

    def _move(key: str) -> str | None:
        src = outputs.get(key)
        if not src or not Path(src).exists():
            return None
        dest = dest_dir / Path(src).name
        shutil.move(str(src), str(dest))
        return f"{base}/uploads/videos/{user_id}/{video.id}/{dest.name}"

    video.video_short_url = _move("video_short")
    video.video_long_url = _move("video_long")
    video.srt_short_url = _move("srt_short")
    video.srt_long_url = _move("srt_long")
    video.thumbnail_url = _move("thumbnail")

    meta_path = outputs.get("metadata")
    if meta_path and Path(meta_path).exists():
        meta = json.loads(Path(meta_path).read_text())
        video.title = meta.get("title")
        video.hashtags = meta.get("hashtags")
        video.youtube_title = meta.get("youtube_title")
        video.youtube_description = meta.get("youtube_description")
        video.tiktok_caption = meta.get("tiktok_caption")
        video.metadata_json = meta


async def generate_in_background(video_id: int) -> None:
    """The actual job — runs after the API has already returned 202 to the
    client. Owns its own DB session since it outlives the request."""
    async with SessionLocal() as db:
        video = await db.get(GeneratedVideo, video_id)
        if video is None:
            return
        channel = await db.get(VideoChannel, video.channel_id)
        user = await db.get(User, video.user_id)
        if channel is None or user is None:
            video.status, video.error = FAILED, "Channel or user no longer exists."
            await db.commit()
            return

        video.status = GENERATING
        video.started_at = datetime.now(timezone.utc)
        await db.commit()

        channel_dict = channel.to_pipeline_dict()
        loop = asyncio.get_running_loop()
        try:
            outputs = await loop.run_in_executor(
                _EXECUTOR, _run_pipeline_blocking, channel.id, channel_dict, video.topic
            )
            _persist_outputs(video, outputs, user.id)
            # Charge only after a successful generation — never on failure.
            try:
                await credits.charge(db, user, credits.COST_VIDEO)
            except Exception:
                # The has_credits() pre-check at submission time (app/api/videos.py)
                # already tried to prevent this; landing here means a losing race
                # against another concurrent charge. The video itself is real and
                # already generated — surface the billing issue as a note rather
                # than discarding finished work.
                video.error = "Generated, but ran out of credits before the charge completed."
            video.status = COMPLETED
            video.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            log.warning("Video generation failed for video_id=%s: %s", video_id, exc)
            video.status = FAILED
            video.error = str(exc)[:2000]
        await db.commit()


def schedule_generation(video_id: int) -> None:
    """Fire-and-forget: schedule generate_in_background() on the running
    event loop, keeping a reference so the task survives past this call."""
    task = asyncio.create_task(generate_in_background(video_id))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
