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
from app.core.config import settings, FEATURE_PERMISSIONS
from app.core.security import (
    create_access_token,
    encrypt_secret,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.email_verification import EmailVerificationToken
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.core import credits
from app.core.entitlements import effective_entitlements, is_admin
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SetAutomationRequest,
    SetHubKeyRequest,
    SetProfileRequest,
    SetZernioKeyRequest,
    TokenResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.services.email import (
    reset_email_html,
    send_email,
    verification_email_html,
    welcome_email_html,
)


import logging

log = logging.getLogger("uvicorn.error")


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.has_hub_key = bool(user.hub_api_key_enc)
    out.has_zernio_key = bool(user.zernio_api_key_enc)
    out.entitlements = effective_entitlements(user)
    out.is_admin = is_admin(user)
    out.email_verified = user.email_verified
    out.subscribed = credits.is_subscribed(user)
    out.free_today_remaining = credits.free_remaining(user)
    out.trial_ends_at = user.trial_ends_at
    # Populate available features based on profile_type
    if user.profile_type and user.profile_type in FEATURE_PERMISSIONS:
        out.available_features = sorted(list(FEATURE_PERMISSIONS[user.profile_type]))
    return out


async def _send_verification(user: User, db: AsyncSession) -> None:
    """Create a verification token and email the user a confirm link."""
    raw = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    ))
    await db.commit()
    base = (settings.app_base_url or "").rstrip("/")
    verify_url = f"{base}/#verify?token={raw}"
    html, text = verification_email_html(verify_url)
    sent = await send_email(
        to=user.email, subject="Verify your email",
        html=html, text=text,
    )
    # Logged so the link is retrievable if email delivery is misconfigured.
    log.info("Email verification for %s (sent=%s): %s", user.email, sent, verify_url)


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    if (
        settings.admin_email
        and body.email.strip().lower() == settings.admin_email.strip().lower()
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This email address cannot self-register."
        )

    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Auto-verify all users — no email gate during beta.
    # Once Mailjet's sender verification for MAILJET_FROM is confirmed working
    # (it can then deliver to any recipient), flip this to require real
    # email verification.
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if settings.email_enabled:
        try:
            app_url = (settings.app_base_url or "").rstrip("/") or "https://autopilot-io.up.railway.app"
            html, text = welcome_email_html(user.full_name, app_url)
            await send_email(
                to=user.email,
                subject="Welcome to Autopilot — your AI marketing team is ready",
                html=html, text=text,
            )
        except Exception as e:
            log.warning("Welcome email failed for %s: %s", user.email, e)

    return {
        "ok": True,
        "verification_required": False,
        "message": "Account created — you're all set.",
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


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
    if not user.email_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Please verify your email first — check your inbox for the link.",
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(
    body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Confirm an email with a valid, unused, unexpired token, then sign in."""
    row = await db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == _hash_token(body.token),
            EmailVerificationToken.used.is_(False),
        )
    )
    exp = row.expires_at if row else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if not row or exp is None or exp < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link.")
    user = await db.get(User, row.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link.")
    user.email_verified = True
    row.used = True
    await db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Resend a verification link. Enumeration-safe (same response either way)."""
    generic = {"ok": True, "message": "If that account needs verifying, a new link is on its way."}
    user = await db.scalar(select(User).where(User.email == body.email))
    if user and not user.email_verified and settings.email_enabled:
        await _send_verification(user, db)
    return generic


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
        html, text = reset_email_html(reset_url)
        sent = await send_email(
            to=user.email, subject="Reset your password",
            html=html, text=text,
        )
        log.info("Password reset for %s (sent=%s): %s", user.email, sent, reset_url)
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
