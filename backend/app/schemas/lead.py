"""Lead (CRM-lite) request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_STATUS = "^(new|contacted|qualified|won|lost)$"


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    handle: str | None = None
    platform: str | None = None
    source: str | None = None
    notes: str | None = None


class LeadUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    handle: str | None = None
    platform: str | None = None
    source: str | None = None
    status: str | None = Field(None, pattern=_STATUS)
    notes: str | None = None
    draft: str | None = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    handle: str | None
    platform: str | None
    source: str | None
    status: str
    notes: str | None
    draft: str | None
    created_at: datetime


class DraftOutreachRequest(BaseModel):
    angle: str = "warm, helpful introduction"
    goal: str = "start a conversation and offer value"
