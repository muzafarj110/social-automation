"""Profile Studio request schemas (field names match the Hub's OpenAPI)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileOptimizeRequest(BaseModel):
    current_headline: str = Field(..., min_length=1)
    current_summary: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    industry: str = Field(..., min_length=1)
    goals: str | None = None


class HeadlineVariantsRequest(BaseModel):
    current_headline: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    industry: str | None = None
    goal: str | None = None
    keywords: str | None = None


class FeaturedSectionRequest(BaseModel):
    role: str = Field(..., min_length=1)
    industry: str | None = None
    goal: str | None = None
    current_featured: str | None = None
    links_available: str | None = None


class RecommendationRequest(BaseModel):
    person_name: str = Field(..., min_length=1)
    person_role: str = Field(..., min_length=1)
    your_role: str = Field(..., min_length=1)
    relationship: str = Field(..., min_length=1)
    key_achievement: str = Field(..., min_length=1)
    key_quality: str = Field(..., min_length=1)
    tone: str = "warm and professional"
