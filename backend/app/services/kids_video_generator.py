"""
Kids video generator — orchestrates AI-powered educational video generation.

Pipeline stages:
  1. Script Generation (Claude Haiku) — topic + age + theme → structured script
  2. Image Generation (DALL-E 3) — scenes + color palette → illustrated images
  3. Music Selection (Royalty-Free Library) — tone + pacing → music track
  4. Composition (FFmpeg) — images + TTS + music → MP4 video

Like the faceless pipeline, this owns its own DB session and runs
generation in the background, charging credits only on success.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core import credits
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.generated_video import COMPLETED, FAILED, GENERATING, GeneratedVideo
from app.models.user import User
from app.models.video_channel import VideoChannel

log = logging.getLogger("uvicorn.error")

_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# Generation status stages
STAGE_SCRIPT = "script_generated"
STAGE_IMAGES = "images_generated"
STAGE_MUSIC = "music_selected"
STAGE_COMPOSED = "composed"
STAGE_READY = "ready_for_approval"

# Credit costs for kids video generation components
COST_KIDS_VIDEO = 12


async def generate_in_background(video_id: int) -> None:
    """
    Main generation job — runs after API returns 202 to client.
    Owns its own DB session (outlives the request).
    """
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

        try:
            # Stage 1: Generate script via Claude
            video.generation_status = STAGE_SCRIPT
            await db.commit()
            script_data = await _generate_script(
                topic=video.topic,
                channel=channel,
                generation_metadata=video.generation_metadata or {},
            )
            log.info(f"Generated script for video {video_id}")

            # Stage 2: Generate images via DALL-E 3
            video.generation_status = STAGE_IMAGES
            await db.commit()
            images_data = await _generate_images(
                script=script_data,
                channel=channel,
                generation_metadata=video.generation_metadata or {},
            )
            log.info(f"Generated {len(images_data.get('image_urls', []))} images for video {video_id}")

            # Stage 3: Select music from royalty-free library
            video.generation_status = STAGE_MUSIC
            await db.commit()
            music_data = await _select_music(
                tone=script_data.get("music_suggestion", "upbeat"),
                channel=channel,
            )
            log.info(f"Selected music for video {video_id}: {music_data.get('music_url', 'N/A')}")

            # Stage 4: Compose video (FFmpeg: images + TTS + music)
            video.generation_status = STAGE_COMPOSED
            await db.commit()
            loop = asyncio.get_running_loop()
            outputs = await loop.run_in_executor(
                _EXECUTOR,
                _compose_video_blocking,
                video_id,
                script_data,
                images_data,
                music_data,
                user.id,
            )
            log.info(f"Composed video {video_id}")

            # Persist outputs
            _persist_outputs(video, outputs, user.id)

            # Charge credits only after successful generation
            try:
                await credits.charge(db, user, COST_KIDS_VIDEO)
            except Exception as exc:
                log.warning(f"Credit charge failed for video {video_id}: {exc}")
                video.error = "Generated, but ran out of credits before the charge completed."

            video.status = COMPLETED
            video.generation_status = STAGE_READY
            video.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            log.error(f"Kids video generation failed for video_id={video_id}: {exc}")
            video.status = FAILED
            video.error = str(exc)[:2000]

        await db.commit()


async def _generate_script(topic: str, channel: VideoChannel, generation_metadata: dict) -> dict:
    """
    Generate educational script via Claude Haiku.
    Returns structured script with scenes and narration.
    """
    # TODO: Implement Claude Hub integration for script generation
    # For now, return placeholder
    return {
        "title": f"Learning {topic}",
        "scenes": [
            {
                "number": 1,
                "duration_seconds": 10,
                "narration": f"Hello friends! Today we're learning about {topic}!",
                "visual_description": "Bright cheerful character waving at screen",
            }
        ],
        "music_suggestion": channel.music_preference or "upbeat",
    }


async def _generate_images(script: dict, channel: VideoChannel, generation_metadata: dict) -> dict:
    """
    Generate illustrated scene images via DALL-E 3.
    Returns URLs for each scene image.
    """
    # TODO: Implement DALL-E 3 integration for image generation
    # For now, return placeholder
    return {
        "image_urls": ["https://placeholder.com/image1.jpg"],
        "character_style": channel.character_style,
        "color_palette": channel.color_palette,
    }


async def _select_music(tone: str, channel: VideoChannel) -> dict:
    """
    Select background music from royalty-free library.
    Returns music metadata (URL, duration, etc).
    """
    # TODO: Implement royalty-free music library integration
    # For now, return placeholder
    return {
        "music_url": "https://placeholder.com/music.mp3",
        "music_title": "Upbeat Kids Music",
        "duration_seconds": 180,
    }


def _compose_video_blocking(
    video_id: int,
    script: dict,
    images: dict,
    music: dict,
    user_id: int,
) -> dict:
    """
    Compose final video via FFmpeg (runs on worker thread).
    Returns dict with output file paths.
    """
    # TODO: Implement FFmpeg composition logic
    # This should:
    # 1. Generate TTS narration from script (using edge-tts)
    # 2. Sequence images with crossfade transitions
    # 3. Mix narration + music at appropriate levels
    # 4. Generate SRT subtitles from narration
    # 5. Create thumbnail
    # Return paths to all outputs
    return {
        "video_short": "/tmp/video_short.mp4",
        "thumbnail": "/tmp/thumbnail.jpg",
        "metadata": "/tmp/metadata.json",
    }


def _persist_outputs(video: GeneratedVideo, outputs: dict, user_id: int) -> None:
    """
    Move pipeline outputs into upload_dir and build public URLs.
    Matches existing media.py upload convention.
    """
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
    video.thumbnail_url = _move("thumbnail")

    meta_path = outputs.get("metadata")
    if meta_path and Path(meta_path).exists():
        meta = json.loads(Path(meta_path).read_text())
        video.title = meta.get("title")
        video.metadata_json = meta


def schedule_generation(video_id: int) -> None:
    """
    Fire-and-forget: schedule generate_in_background() on the event loop.
    Keeps a reference so the task survives past this call.
    """
    task = asyncio.create_task(generate_in_background(video_id))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
