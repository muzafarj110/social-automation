"""
Admin API — operator dashboard for a subscription product.

An admin (the configured ADMIN_EMAIL) can list every user, change their plan,
suspend/reactivate them, and override individual feature entitlements. All
routes are gated by `require_admin`. No secrets are ever returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import settings
from app.core.entitlements import (
    FEATURES,
    PLAN_FEATURES,
    effective_entitlements,
    is_admin,
)
from app.db.session import get_db
from app.models.account import LinkedInAccount
from app.models.user import User
from app.schemas.admin import AdminFeaturesOut, AdminUserOut, AdminUserUpdate
from app.services import email as email_svc

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/email-config")
async def email_config(_: User = Depends(require_admin)) -> dict:
    """Return current email config status so admin can debug delivery issues."""
    return {
        "email_enabled": settings.email_enabled,
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user or "(not set)",
        "smtp_pass_set": bool(settings.smtp_pass),
        "smtp_from": settings.smtp_from or f"Autopilot <{settings.smtp_user}>",
        "app_base_url": settings.app_base_url or "(not set — links will be broken)",
    }


@router.post("/test-email")
async def test_email(current: User = Depends(require_admin)) -> dict:
    """Send a test email to the admin address. Returns ok + any error detail."""
    if not settings.email_enabled:
        return {
            "ok": False,
            "error": "Email is disabled — SMTP_USER and/or SMTP_PASS are not set in Railway.",
        }
    import asyncio, smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    error: str | None = None
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Autopilot — test email"
        msg["From"] = settings.smtp_from or f"Autopilot <{settings.smtp_user}>"
        msg["To"] = current.email
        msg.attach(MIMEText(
            "<p>This is a test email from Autopilot. If you see this, email delivery is working!</p>",
            "html",
        ))
        ctx = ssl.create_default_context()
        def _send():
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.login(settings.smtp_user, settings.smtp_pass)
                s.sendmail(msg["From"], [current.email], msg.as_string())
        await asyncio.to_thread(_send)
    except smtplib.SMTPAuthenticationError as e:
        error = f"Authentication failed: {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e}"
    except smtplib.SMTPException as e:
        error = f"SMTP error: {e}"
    except Exception as e:
        error = f"Connection error: {e}"

    if error:
        return {"ok": False, "error": error, "sent_to": current.email}
    return {"ok": True, "sent_to": current.email, "message": "Test email sent — check your inbox."}


def _to_out(user: User, account_count: int) -> AdminUserOut:
    out = AdminUserOut.model_validate(user)
    out.is_admin = is_admin(user)
    out.has_hub_key = bool(user.hub_api_key_enc)
    out.has_zernio_key = bool(user.zernio_api_key_enc)
    out.account_count = account_count
    out.entitlements = effective_entitlements(user)
    out.entitlements_override = user.entitlements_override
    return out


@router.get("/features", response_model=AdminFeaturesOut)
async def list_features(_: User = Depends(require_admin)) -> AdminFeaturesOut:
    """The set of gateable features and each plan's defaults (for the UI)."""
    return AdminFeaturesOut(features=FEATURES, plan_features=PLAN_FEATURES)


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserOut]:
    """Every user, newest first, with effective features and read-only signals."""
    users = list(await db.scalars(select(User).order_by(User.created_at.desc())))
    counts = dict(
        (await db.execute(
            select(LinkedInAccount.user_id, func.count(LinkedInAccount.id))
            .group_by(LinkedInAccount.user_id)
        )).all()
    )
    return [_to_out(u, int(counts.get(u.id, 0))) for u in users]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    body: AdminUserUpdate,
    current: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserOut:
    """Change a user's plan, status, or feature overrides."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Guard rails: an admin can't lock themselves out.
    if is_admin(user) and body.status == "suspended":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Can't suspend an admin account")

    data = body.model_dump(exclude_unset=True)
    if "plan" in data:
        user.plan = data["plan"]
    if "status" in data:
        user.status = data["status"]
    if "entitlements_override" in data:
        ov = data["entitlements_override"]
        # keep only known feature keys; empty/None clears the override
        user.entitlements_override = (
            {k: bool(v) for k, v in ov.items() if k in FEATURES} if ov else None
        )

    await db.commit()
    await db.refresh(user)

    count = await db.scalar(
        select(func.count(LinkedInAccount.id)).where(LinkedInAccount.user_id == user.id)
    )
    return _to_out(user, int(count or 0))
