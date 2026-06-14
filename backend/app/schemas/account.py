"""Social account schemas (any platform)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.platforms import PLATFORM_PATTERN


class ConnectRequest(BaseModel):
    platform: str = Field("linkedin", pattern=PLATFORM_PATTERN)
    # Where to send the user back after they authorize (the app's own URL).
    redirect_url: str | None = None


class LinkAccountRequest(BaseModel):
    zernio_account_id: str = Field(..., min_length=1)
    platform: str = Field("linkedin", pattern=PLATFORM_PATTERN)
    account_type: str = Field("personal", pattern="^(personal|organization)$")
    display_name: str | None = None
    avatar_url: str | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    zernio_account_id: str
    account_type: str
    display_name: str | None
    avatar_url: str | None
    status: str
    connected_at: datetime
    last_synced_at: datetime | None
