from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProactiveItemOut(BaseModel):
    id: int
    agent: str
    title: str
    body: str
    action_tab: str | None
    status: str
    generated_at: datetime

    class Config:
        from_attributes = True
