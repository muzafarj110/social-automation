"""Post request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    account_id: int
    body: str = Field(..., min_length=1)
    hashtags: list[str] | None = None
    media: list[dict[str, Any]] | None = None
    first_comment: str | None = None
    infographic_html: str | None = None


class PostUpdate(BaseModel):
    body: str | None = Field(None, min_length=1)
    hashtags: list[str] | None = None
    media: list[dict[str, Any]] | None = None
    first_comment: str | None = None


class ScheduleRequest(BaseModel):
    scheduled_for: datetime
    timezone: str = "UTC"


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    platform: str
    body: str
    hashtags: list[str] | None
    media: list[dict[str, Any]] | None
    first_comment: str | None
    status: str
    scheduled_for: datetime | None
    timezone: str
    zernio_post_id: str | None
    platform_post_url: str | None
    error: str | None
    source: str
    has_infographic: bool = False
    team_run_id: int | None = None
    qa_score: int | None = None
    created_at: datetime
    updated_at: datetime
