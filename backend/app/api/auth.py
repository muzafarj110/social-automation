"""Auth routes: register, login, me, set Hub key."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    encrypt_secret,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.core.entitlements import effective_entitlements
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SetHubKeyRequest,
    SetProfileRequest,
    SetZernioKeyRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.has_hub_key = bool(user.hub_api_key_enc)
    out.has_zernio_key = bool(user.zernio_api_key_enc)
    out.entitlements = effective_entitlements(user)
    return out


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # OAuth2 form uses `username` — we treat it as the email.
    user = await db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current)


@router.put("/me/hub-key", response_model=UserOut)
async def set_hub_key(
    body: SetHubKeyRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Store the user's own AI Models Hub API key (encrypted at rest)."""
    current.hub_api_key_enc = encrypt_secret(body.hub_api_key)
    await db.commit()
    await db.refresh(current)
    return _user_out(current)


@router.put("/me/profile", response_model=UserOut)
async def set_profile(
    body: SetProfileRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Onboarding: record the user's profile type so the workspace adapts."""
    current.profile_type = body.profile_type
    await db.commit()
    await db.refresh(current)
    return _user_out(current)


@router.put("/me/zernio-key", response_model=UserOut)
async def set_zernio_key(
    body: SetZernioKeyRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Store the user's own Zernio API key (encrypted at rest). This scopes
    which LinkedIn accounts the user can see and post to."""
    current.zernio_api_key_enc = encrypt_secret(body.zernio_api_key)
    await db.commit()
    await db.refresh(current)
    return _user_out(current)
