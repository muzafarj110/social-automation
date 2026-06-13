"""Admin dashboard request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserOut(BaseModel):
    """A user as seen by an admin — status, plan, effective features, and a few
    read-only signals (key presence, account count). Never includes secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    plan: str
    status: str
    profile_type: str | None = None
    is_admin: bool = False
    has_hub_key: bool = False
    has_zernio_key: bool = False
    account_count: int = 0
    entitlements: dict[str, bool] = {}
    entitlements_override: dict[str, bool] | None = None
    created_at: datetime


class AdminUserUpdate(BaseModel):
    """Partial update — only the provided fields change."""

    plan: str | None = Field(None, pattern="^(free|pro|business)$")
    status: str | None = Field(None, pattern="^(active|suspended)$")
    # Per-feature overrides merged over the plan defaults. Send {} to clear.
    entitlements_override: dict[str, bool] | None = None


class AdminFeaturesOut(BaseModel):
    """The full list of gateable feature keys + which plans unlock what, so the
    dashboard can render the right checkboxes."""

    features: list[str]
    plan_features: dict[str, dict[str, bool]]
