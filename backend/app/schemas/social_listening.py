from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TopicCreate(BaseModel):
    keyword: str
    description: str | None = None
    platform: str = "linkedin"


class TopicUpdate(BaseModel):
    keyword: str | None = None
    description: str | None = None
    platform: str | None = None


class TopicOut(BaseModel):
    id: int
    keyword: str
    description: str | None
    platform: str
    results: dict | None
    scanned_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
