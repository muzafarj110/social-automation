"""Campaign (autopilot) request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.platforms import PLATFORMS


def _validate_platforms(v: list[str] | None) -> list[str] | None:
    if v is None:
        return v
    cleaned = [p.strip().lower() for p in v if p and p.strip().lower() in PLATFORMS]
    # de-dupe, preserve order
    seen: set[str] = set()
    out = [p for p in cleaned if not (p in seen or seen.add(p))]
    return out or None


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    account_id: int
    # Platforms to post to. Empty = just the linked account's platform.
    platforms: list[str] | None = Field(None, description="e.g. ['linkedin','twitter']")
    mode: str = Field("approve", pattern="^(auto|approve)$")
    topic_source: str = Field("topics", pattern="^(topics|goal)$")
    topics: list[str] | None = None
    niche: str | None = None
    goal: str | None = None
    audience: str | None = None
    tone: str = "professional but human"
    post_type: str = "Personal Story + Lesson"
    post_types: list[str] | None = None    # angles to rotate (falls back to post_type)
    frequency_per_week: int = Field(3, ge=1, le=14)
    days: list[int] | None = None          # 0=Mon .. 6=Sun
    time_of_day: str = Field("09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = "UTC"
    ai_timing: bool = False                # let the Hub suggest posting days/times
    auto_improve: bool = True              # QA + auto-polish each generated post
    with_infographic: bool = False         # generate an infographic alongside each post
    learn_from_analytics: bool = False     # bias topics toward best-performing posts

    @field_validator("platforms")
    @classmethod
    def _v_platforms(cls, v: list[str] | None) -> list[str] | None:
        return _validate_platforms(v)


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    platforms: list[str] | None = None
    mode: str | None = Field(None, pattern="^(auto|approve)$")
    topic_source: str | None = Field(None, pattern="^(topics|goal)$")
    topics: list[str] | None = None
    niche: str | None = None
    goal: str | None = None
    audience: str | None = None
    tone: str | None = None
    post_type: str | None = None
    post_types: list[str] | None = None
    frequency_per_week: int | None = Field(None, ge=1, le=14)
    days: list[int] | None = None
    time_of_day: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str | None = None
    ai_timing: bool | None = None
    auto_improve: bool | None = None
    with_infographic: bool | None = None
    learn_from_analytics: bool | None = None
    status: str | None = Field(None, pattern="^(active|paused)$")

    @field_validator("platforms")
    @classmethod
    def _v_platforms(cls, v: list[str] | None) -> list[str] | None:
        return _validate_platforms(v)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    name: str
    platforms: list[str] | None
    mode: str
    topic_source: str
    topics: list[str] | None
    niche: str | None
    goal: str | None
    audience: str | None
    tone: str
    post_type: str
    post_types: list[str] | None
    frequency_per_week: int
    days: list[int] | None
    time_of_day: str
    timezone: str
    ai_timing: bool
    auto_improve: bool
    with_infographic: bool
    learn_from_analytics: bool
    status: str
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_error: str | None
    created_at: datetime
