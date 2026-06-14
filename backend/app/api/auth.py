"""Auth routes: register, login, me, keys, password reset."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    encrypt_secret,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.core.entitlements import effective_entitlements, is_admin
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SetAutomationRequest,
    SetHubKeyRequest,
    SetProfileRequest,
    SetZernioKeyRequest,
    TokenResponse,
    UserOut,
)
from app.services.email import reset_email_html, send_email


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.has_hub_key = bool(user.hub_api_key_enc)
    out.has_zernio_key = bool(user.zernio_api_key_enc)
    out.entitlements = effective_entitlements(user)
    out.is_admin = is_admin(user)
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


@router.put("/me/password", response_model=UserOut)
async def change_password(
    body: ChangePasswordRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Change password while logged in (verifies the current password first)."""
    if not verify_password(body.current_password, current.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    current.password_hash = hash_password(body.new_password)
    await db.commit()
    await db.refresh(current)
    return _user_out(current)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Email a password-reset link. Always returns the same response whether or
    not the email exists, so it can't be used to discover accounts."""
    generic = {"ok": True,
               "message": "If that email is registered, a reset link is on its way."}
    user = await db.scalar(select(User).where(User.email == body.email))
    if user and settings.email_enabled:
        raw = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        await db.commit()
        base = (settings.app_base_url or "").rstrip("/")
        reset_url = f"{base}/#reset?token={raw}"
        await send_email(
            to=user.email, subject="Reset your password",
            html=reset_email_html(reset_url),
        )
    return generic


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Set a new password using a valid, unused, unexpired reset token."""
    row = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash_token(body.token),
            PasswordResetToken.used.is_(False),
        )
    )
    exp = row.expires_at if row else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if not row or exp is None or exp < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link.")

    user = await db.get(User, row.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link.")
    user.password_hash = hash_password(body.new_password)
    row.used = True
    await db.commit()
    # Log them straight in after a successful reset.
    return TokenResponse(access_token=create_access_token(user.id))


@router.put("/me/automation", response_model=UserOut)
async def set_automation(
    body: SetAutomationRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Global pause/resume: when paused, no campaign auto-publishes — everything
    becomes a draft to approve. The user's safety net."""
    current.automation_paused = body.paused
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
