"""Video agent request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VideoChannelIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    handle: str = Field(..., min_length=1, max_length=120)
    niche: str = Field(..., min_length=1)
    accent_color: str = "#7c4dff"
    music_style: str = "calm"
    tts_voice: str | None = None
    claude_system_prompt: str | None = None
    pexels_fallback_keywords: list[str] | None = None
    short_clips: int = 6
    long_clips: int = 18
    clip_duration: int = 8
    pexels_orientation: str = "portrait"
    cache_duration_days: int = 7


class VideoChannelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    handle: str | None = Field(None, min_length=1, max_length=120)
    niche: str | None = Field(None, min_length=1)
    accent_color: str | None = None
    music_style: str | None = None
    tts_voice: str | None = None
    claude_system_prompt: str | None = None
    pexels_fallback_keywords: list[str] | None = None
    short_clips: int | None = None
    long_clips: int | None = None
    clip_duration: int | None = None
    pexels_orientation: str | None = None
    cache_duration_days: int | None = None


class VideoChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    handle: str
    niche: str
    accent_color: str
    music_style: str
    tts_voice: str | None
    claude_system_prompt: str | None
    pexels_fallback_keywords: list[str] | None
    short_clips: int
    long_clips: int
    clip_duration: int
    pexels_orientation: str
    cache_duration_days: int
    created_at: datetime
    updated_at: datetime


class GenerateVideoRequest(BaseModel):
    topic: str = Field(..., min_length=1)


class GeneratedVideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    topic: str
    status: str
    progress_step: str | None
    error: str | None
    title: str | None
    hashtags: list[str] | None
    youtube_title: str | None
    youtube_description: str | None
    tiktok_caption: str | None
    video_short_url: str | None
    video_long_url: str | None
    thumbnail_url: str | None
    short_post_id: int | None
    long_post_id: int | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CreatePostFromVideoRequest(BaseModel):
    account_id: int
    variant: Literal["short", "long"]
