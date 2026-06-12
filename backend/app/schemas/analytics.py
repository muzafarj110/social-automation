"""Analytics request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InsightsRequest(BaseModel):
    """Account metrics → Hub linkedin-analytics interpretation."""

    followers: int = Field(0, ge=0)
    impressions: int = Field(0, ge=0)
    profile_views: int = Field(0, ge=0)
    post_count: int = Field(0, ge=0)
    avg_likes: int = Field(0, ge=0)
    avg_comments: int = Field(0, ge=0)
    avg_shares: int = Field(0, ge=0)
    timeframe: str = "Last 30 days"
    goal: str | None = None


class ViralRequest(BaseModel):
    """One post's text + metrics → Hub viral-analyzer."""

    post: str = Field(..., min_length=1)
    niche: str | None = None
    impressions: int = Field(0, ge=0)
    likes: int = Field(0, ge=0)
    comments: int = Field(0, ge=0)
    shares: int = Field(0, ge=0)
