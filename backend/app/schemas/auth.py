"""Auth + user request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    plan: str
    status: str
    created_at: datetime
    has_hub_key: bool = False
    has_zernio_key: bool = False
    profile_type: str | None = None
    entitlements: dict[str, bool] = {}
    is_admin: bool = False


class SetProfileRequest(BaseModel):
    profile_type: str = Field(..., pattern="^(individual|influencer|startup|company)$")


class SetHubKeyRequest(BaseModel):
    hub_api_key: str = Field(..., min_length=8)


class SetZernioKeyRequest(BaseModel):
    zernio_api_key: str = Field(..., min_length=8)
