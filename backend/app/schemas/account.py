"""LinkedIn account schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LinkAccountRequest(BaseModel):
    zernio_account_id: str = Field(..., min_length=1)
    account_type: str = Field("personal", pattern="^(personal|organization)$")
    display_name: str | None = None
    avatar_url: str | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zernio_account_id: str
    account_type: str
    display_name: str | None
    avatar_url: str | None
    status: str
    connected_at: datetime
    last_synced_at: datetime | None
