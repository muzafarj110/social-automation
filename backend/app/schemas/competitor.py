"""Competitor (Competitor Strategy agent) request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    website: str | None = None
    notes: str | None = None


class CompetitorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    website: str | None = None
    notes: str | None = None


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website: str | None
    notes: str | None
    # `analysis` is stored as a JSON string; the API parses it into this object.
    analysis: dict | None = None
    analyzed_at: datetime | None
    created_at: datetime
