"""Kids video channel and generation schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KidsVideoChannelCreate(BaseModel):
    """Request to create a kids video channel."""
    name: str = Field(..., min_length=1, max_length=120)
    target_age_min: int = Field(default=0, ge=0, le=10)
    target_age_max: int = Field(default=5, ge=0, le=10)
    primary_theme: str = Field(..., min_length=1, max_length=50)
    character_style: str = Field(..., min_length=1, max_length=255)
    color_palette: list[str] = Field(default_factory=lambda: ["#FF6B6B", "#4ECDC4", "#FFE66D"])
    music_preference: str = Field(default="upbeat", pattern="^(upbeat|calm|playful)$")


class KidsVideoChannelUpdate(BaseModel):
    """Request to update a kids video channel."""
    name: str | None = Field(None, min_length=1, max_length=120)
    target_age_min: int | None = Field(None, ge=0, le=10)
    target_age_max: int | None = Field(None, ge=0, le=10)
    primary_theme: str | None = Field(None, min_length=1, max_length=50)
    character_style: str | None = Field(None, min_length=1, max_length=255)
    color_palette: list[str] | None = None
    music_preference: str | None = Field(None, pattern="^(upbeat|calm|playful)$")


class KidsVideoChannelOut(BaseModel):
    """Response for a kids video channel."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    target_age_min: int
    target_age_max: int
    primary_theme: str | None
    character_style: str | None
    color_palette: str | None
    music_preference: str | None
    content_type: str
    created_at: datetime
    updated_at: datetime


class KidsVideoGenerationRequest(BaseModel):
    """Request to generate a kids video."""
    channel_id: int
    topic: str = Field(..., min_length=1, max_length=1000)
    learning_goal: str = Field(..., min_length=1, max_length=1000)
    tone: str = Field(default="upbeat", pattern="^(upbeat|calm|silly)$")


class KidsVideoAssetCreate(BaseModel):
    """Request to create a kids video asset."""
    channel_id: int
    asset_type: str = Field(..., pattern="^(character|background|prop)$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    image_url: str = Field(..., min_length=10)
    metadata_json: dict[str, Any] | None = None


class KidsVideoAssetOut(BaseModel):
    """Response for a kids video asset."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    channel_id: int
    asset_type: str
    name: str
    description: str | None
    image_url: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class GeneratedKidsVideoOut(BaseModel):
    """Response for a generated kids video."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    channel_id: int
    topic: str
    status: str
    content_type: str
    progress_step: str | None
    generation_status: str | None
    error: str | None
    video_short_url: str | None
    video_long_url: str | None
    thumbnail_url: str | None
    generation_metadata: dict[str, Any] | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class GeneratedKidsVideoProgressOut(BaseModel):
    """Response for video generation progress."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    progress_step: str | None
    generation_status: str | None
    error: str | None
    generation_metadata: dict[str, Any] | None
