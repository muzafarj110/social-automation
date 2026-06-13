"""Brand profile (strategy brain) schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BrandProfileUpdate(BaseModel):
    brand_name: str | None = None
    industry: str | None = None
    audience: str | None = None
    voice: str | None = None
    mission: str | None = None
    positioning: str | None = None
    docs: dict[str, Any] | None = None


class BrandProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_name: str | None = None
    industry: str | None = None
    audience: str | None = None
    voice: str | None = None
    mission: str | None = None
    positioning: str | None = None
    docs: dict[str, Any] | None = None


class BrandGenerateRequest(BaseModel):
    # which strategy model to run
    tool: str = Field(..., pattern="^(brand_voice|customer_persona|uvp|competitor_analysis|content_strategy)$")
    params: dict[str, Any] = Field(default_factory=dict)
