from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SeoProjectCreate(BaseModel):
    website: str | None = None
    target_keywords: str
    audience: str | None = None


class SeoProjectUpdate(BaseModel):
    website: str | None = None
    target_keywords: str | None = None
    audience: str | None = None


class SeoProjectOut(BaseModel):
    id: int
    website: str | None
    target_keywords: str
    audience: str | None
    results: dict | None
    analyzed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
