"""Video agent API — channel config, async generate+poll, gallery, Posts hand-off."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.posts import _get_owned_account
from app.core import credits
from app.core.clients import client_scope
from app.core.config import settings
from app.db.session import get_db
from app.models import post as post_status
from app.models.generated_video import COMPLETED, GeneratedVideo, QUEUED
from app.models.post import Post
from app.models.user import User
from app.models.video_channel import VideoChannel
from app.schemas.post import PostOut
from app.schemas.video import (
    CreatePostFromVideoRequest,
    GenerateVideoRequest,
    GeneratedVideoOut,
    VideoChannelIn,
    VideoChannelOut,
    VideoChannelUpdate,
)
from app.services import video_generator

router = APIRouter(prefix="/videos", tags=["videos"])


async def _get_owned_channel(current: User, db: AsyncSession) -> VideoChannel:
    channel = await db.scalar(
        select(VideoChannel).where(
            VideoChannel.user_id == current.id,
            client_scope(VideoChannel.client_id, current.active_client_id),
        )
    )
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No video channel configured yet.")
    return channel


async def _get_owned_video(video_id: int, current: User, db: AsyncSession) -> GeneratedVideo:
    video = await db.get(GeneratedVideo, video_id)
    if not video or video.user_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return video


@router.get("/channel", response_model=VideoChannelOut)
async def get_channel(
    current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> VideoChannel:
    return await _get_owned_channel(current, db)


@router.post("/channel", response_model=VideoChannelOut, status_code=201)
async def create_channel(
    body: VideoChannelIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoChannel:
    existing = await db.scalar(
        select(VideoChannel).where(
            VideoChannel.user_id == current.id,
            client_scope(VideoChannel.client_id, current.active_client_id),
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A video channel already exists — use PATCH to update it.")
    channel = VideoChannel(
        user_id=current.id, client_id=current.active_client_id, **body.model_dump()
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.patch("/channel", response_model=VideoChannelOut)
async def update_channel(
    body: VideoChannelUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoChannel:
    channel = await _get_owned_channel(current, db)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(channel, k, v)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.post("/generate", response_model=GeneratedVideoOut)
async def generate(
    body: GenerateVideoRequest,
    response: Response,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedVideo:
    if not settings.video_agent_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Video agent isn't configured yet.")
    channel = await _get_owned_channel(current, db)

    # Memory-first: a fresh-enough cached video skips generation entirely.
    cached = await video_generator.find_cached(db, channel, body.topic)
    if cached is not None:
        response.status_code = status.HTTP_200_OK
        return cached

    if not credits.has_credits(current, credits.COST_VIDEO):
        raise HTTPException(402, "You're out of credits. Top up under Billing to keep creating.")

    video = GeneratedVideo(
        user_id=current.id,
        channel_id=channel.id,
        client_id=current.active_client_id,
        topic=body.topic,
        topic_cache_key=video_generator.topic_cache_key(channel.id, body.topic),
        status=QUEUED,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    video_generator.schedule_generation(video.id)
    response.status_code = status.HTTP_202_ACCEPTED
    return video


@router.get("/jobs/{video_id}", response_model=GeneratedVideoOut)
async def get_job(
    video_id: int, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> GeneratedVideo:
    return await _get_owned_video(video_id, current, db)


@router.get("", response_model=list[GeneratedVideoOut])
async def list_videos(
    current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[GeneratedVideo]:
    rows = await db.scalars(
        select(GeneratedVideo)
        .where(
            GeneratedVideo.user_id == current.id,
            client_scope(GeneratedVideo.client_id, current.active_client_id),
        )
        .order_by(GeneratedVideo.requested_at.desc())
    )
    return list(rows)


@router.delete("/{video_id}", status_code=204, response_model=None)
async def delete_video(
    video_id: int, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    video = await _get_owned_video(video_id, current, db)
    for url in (
        video.video_short_url, video.video_long_url,
        video.srt_short_url, video.srt_long_url, video.thumbnail_url,
    ):
        if not url:
            continue
        rel = url.split("/uploads/", 1)[-1]
        Path(settings.upload_dir, rel).unlink(missing_ok=True)
    await db.delete(video)
    await db.commit()


@router.post("/{video_id}/create-post", response_model=PostOut, status_code=201)
async def create_post_from_video(
    video_id: int,
    body: CreatePostFromVideoRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    video = await _get_owned_video(video_id, current, db)
    if video.status != COMPLETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This video hasn't finished generating yet.")

    account = await _get_owned_account(body.account_id, current, db)

    video_url = video.video_short_url if body.variant == "short" else video.video_long_url
    if not video_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No {body.variant} cut is available for this video.")

    caption = video.tiktok_caption if body.variant == "short" else video.youtube_description
    post = Post(
        user_id=current.id,
        account_id=account.id,
        platform=account.platform,
        body=caption or video.title or video.topic,
        hashtags=video.hashtags,
        media=[{"type": "video", "url": video_url}],
        source="generated",
        status=post_status.DRAFT,
        client_id=current.active_client_id,
    )
    db.add(post)
    await db.flush()  # assign post.id
    if body.variant == "short":
        video.short_post_id = post.id
    else:
        video.long_post_id = post.id
    await db.commit()
    await db.refresh(post)
    return post


# ============ Kids Video Agent Routes ============


async def _get_owned_kids_channel(current: User, db: AsyncSession, channel_id: int) -> VideoChannel:
    """Fetch a kids video channel owned by the current user."""
    channel = await db.get(VideoChannel, channel_id)
    if not channel or channel.user_id != current.id or channel.content_type != "kids_educational":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kids video channel not found")
    return channel


@router.post("/kids/channels", response_model=VideoChannelOut, status_code=201)
async def create_kids_channel(
    body,  # TODO: type as KidsVideoChannelCreate from schemas.kids_video
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoChannel:
    """Create a new kids video channel."""
    channel = VideoChannel(
        user_id=current.id,
        client_id=current.active_client_id,
        content_type="kids_educational",
        name=body.name,
        handle=body.name.lower().replace(" ", "_"),
        niche="kids_educational",
        target_age_min=body.target_age_min,
        target_age_max=body.target_age_max,
        primary_theme=body.primary_theme,
        character_style=body.character_style,
        color_palette=",".join(body.color_palette) if body.color_palette else None,
        music_preference=body.music_preference,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.put("/kids/channels/{channel_id}", response_model=VideoChannelOut)
async def update_kids_channel(
    channel_id: int,
    body,  # TODO: type as KidsVideoChannelUpdate
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoChannel:
    """Update a kids video channel."""
    channel = await _get_owned_kids_channel(current, db, channel_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "color_palette" and v is not None:
            v = ",".join(v)
        setattr(channel, k, v)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.post("/kids/generate", response_model=GeneratedVideoOut)
async def generate_kids_video(
    body,  # TODO: type as KidsVideoGenerationRequest
    response: Response,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedVideo:
    """Start a kids video generation job."""
    from app.services import kids_video_generator

    channel = await _get_owned_kids_channel(current, db, body.channel_id)

    if not credits.has_credits(current, kids_video_generator.COST_KIDS_VIDEO):
        raise HTTPException(402, "You're out of credits. Top up under Billing to continue.")

    video = GeneratedVideo(
        user_id=current.id,
        channel_id=channel.id,
        client_id=current.active_client_id,
        topic=body.topic,
        topic_cache_key=video_generator.topic_cache_key(channel.id, body.topic),
        content_type="kids_educational",
        status=QUEUED,
        generation_metadata={
            "learning_goal": body.learning_goal,
            "tone": body.tone,
            "age_min": channel.target_age_min,
            "age_max": channel.target_age_max,
            "theme": channel.primary_theme,
            "character_style": channel.character_style,
        },
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Deduct credits immediately (like faceless videos)
    await credits.charge(db, current, kids_video_generator.COST_KIDS_VIDEO)
    await db.commit()

    # Schedule generation in background
    kids_video_generator.schedule_generation(video.id)
    response.status_code = status.HTTP_202_ACCEPTED
    return video


@router.get("/kids/{video_id}/progress")
async def get_kids_video_progress(
    video_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Poll generation progress."""
    video = await db.get(GeneratedVideo, video_id)
    if not video or video.user_id != current.id or video.content_type != "kids_educational":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return {
        "id": video.id,
        "status": video.status,
        "progress_step": video.progress_step,
        "generation_status": video.generation_status,
        "error": video.error,
    }


@router.post("/kids/{video_id}/approve", response_model=GeneratedVideoOut)
async def approve_kids_video(
    video_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedVideo:
    """Approve a draft kids video to published status."""
    video = await db.get(GeneratedVideo, video_id)
    if not video or video.user_id != current.id or video.content_type != "kids_educational":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    if video.status != COMPLETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only completed videos can be approved")
    # Set a published status or move to a published section
    # For now, we keep it as COMPLETED but could add a publication workflow
    await db.commit()
    await db.refresh(video)
    return video


@router.delete("/kids/{video_id}")
async def delete_kids_video(
    video_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete/reject a draft kids video."""
    video = await db.get(GeneratedVideo, video_id)
    if not video or video.user_id != current.id or video.content_type != "kids_educational":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    # Delete the video and clean up files
    await db.delete(video)
    await db.commit()
    return {"message": "Video deleted"}
