"""
Admin API — operator dashboard for a subscription product.

An admin (the configured ADMIN_EMAIL) can list every user, change their plan,
suspend/reactivate them, and override individual feature entitlements. All
routes are gated by `require_admin`. No secrets are ever returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    return {
        "email_enabled": settings.email_enabled,
        "mailjet_api_key_set": bool(settings.mailjet_api_key),
        "mailjet_secret_key_set": bool(settings.mailjet_secret_key),
        "mailjet_from": settings.mailjet_from or "(not set)",
        "app_base_url": settings.app_base_url or "(not set — links will be broken)",
    }


class TestEmailBody(BaseModel):
    to: str = ""
    include_verify_link: bool = False
    category: str = "generic"


@router.post("/test-email")
async def test_email(
    body: TestEmailBody = TestEmailBody(),
    current: User = Depends(require_admin),
) -> dict:
    """Send a diagnostic test email via Mailjet. Accepts optional target address
    and a template category to preview."""
    if not settings.email_enabled:
        return {"ok": False, "error": "Email disabled — MAILJET_API_KEY / MAILJET_SECRET_KEY not set in Railway."}

    target = body.to.strip() or current.email
    base = (settings.app_base_url or "").rstrip("/")
    app_base_warn = "(not set — links will be broken!)" if not base else base

    subject = "Autopilot — email test"
    text: str | None = None
    category = body.category or "generic"

    if category == "verification":
        subject = "Confirm your email address for Autopilot"
        html, text = email_svc.verification_email_html(f"{base}/#verify?token=SAMPLE_TOKEN")
    elif category == "reset":
        subject = "Reset your Autopilot password"
        html, text = email_svc.reset_email_html(f"{base}/#reset?token=SAMPLE_TOKEN")
    elif category == "welcome":
        subject = "Welcome to Autopilot — your AI marketing team is ready"
        html, text = email_svc.welcome_email_html("there", base or "https://autopilot-io.up.railway.app")
    elif category == "marketing":
        subject = "Smart Send Times are here: let Autopilot pick your best posting time"
        html, text = email_svc.marketing_email_html(
            headline=subject,
            body_html=(
                "<p style=\"margin:0 0 16px 0;\">Your posts just got smarter. Autopilot now studies when your "
                "audience is actually active and automatically times each post to land in that window — no more "
                "guessing, no more manual scheduling grids.</p>"
                "<p style=\"margin:0 0 16px 0;\">Smart Send Times is live today for every plan. Switch it on from "
                "your workspace settings and Autopilot will handle the timing from here, while you focus on the "
                "message.</p>"
            ),
            body_text=(
                "Your posts just got smarter. Autopilot now studies when your audience is actually active and "
                "automatically times each post to land in that window — no more guessing, no more manual "
                "scheduling grids.\n\nSmart Send Times is live today for every plan. Switch it on from your "
                "workspace settings and Autopilot will handle the timing from here, while you focus on the "
                "message."
            ),
            cta_text="Turn on Smart Send Times",
            cta_url=f"{base or 'https://autopilot-io.up.railway.app'}/#campaigns",
        )
    elif category == "support":
        subject = "We've received your message — Autopilot Support"
        html, text = email_svc.support_email_html(
            name="Jordan Lee",
            message_preview=(
                "Hi, I'm trying to connect my Instagram account but the OAuth screen keeps redirecting back to "
                "the login page. Can you help?"
            ),
        )
    else:
        html = f"""
        <div style='font-family:system-ui,sans-serif;max-width:480px'>
          <h2>Autopilot — email delivery test</h2>
          <p>If you received this, Mailjet can deliver to <b>{target}</b>.</p>
          <hr style='border:none;border-top:1px solid #e5e7eb;margin:16px 0'>
          <p style='font-size:13px;color:#666'><b>APP_BASE_URL:</b> {app_base_warn}</p>
          <p style='font-size:13px;color:#666'>{'<b style="color:red">⚠ APP_BASE_URL is missing — verify/reset links in real emails will be broken.</b>' if not base else '✓ APP_BASE_URL is set correctly.'}</p>
        </div>
        """

    import httpx
    error: str | None = None
    mailjet_response: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            message: dict = {
                "From": {"Email": settings.mailjet_from, "Name": "Autopilot"},
                "To": [{"Email": target}],
                "Subject": subject,
                "HTMLPart": html,
            }
            if text is not None:
                message["TextPart"] = text
            if category == "marketing":
                message["Headers"] = {"List-Unsubscribe": f"<{email_svc.unsubscribe_mailto()}>"}
            r = await c.post(
                "https://api.mailjet.com/v3.1/send",
                auth=(settings.mailjet_api_key, settings.mailjet_secret_key),
                json={"Messages": [message]},
            )
        if r.status_code >= 400:
            mailjet_response = r.text[:400]
            error = f"Mailjet error {r.status_code}: {mailjet_response}"
    except Exception as e:
        error = f"Mailjet connection error: {e}"

    if error:
        return {"ok": False, "error": error, "mailjet_response": mailjet_response, "sent_to": target}
    return {
        "ok": True, "sent_to": target,
        "app_base_url": base or "(not set)",
        "message": f"Sent to {target} via Mailjet. Check inbox + spam.",
    }


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


@router.post("/users/{user_id}/reset-link")
async def generate_reset_link(
    user_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a password reset link for any user. Admin copies it and shares manually."""
    import hashlib, secrets
    from datetime import datetime, timedelta, timezone
    from app.models.password_reset import PasswordResetToken

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    ))
    await db.commit()
    base = (settings.app_base_url or "").rstrip("/")
    reset_url = f"{base}/#reset?token={raw}"
    return {"ok": True, "email": user.email, "reset_url": reset_url, "expires_in": "24 hours"}


@router.delete("/users/{user_id}", status_code=204, response_model=None)
async def delete_user(
    user_id: int,
    current: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete a user and all their data. Cannot delete your own admin account."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if is_admin(user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the admin account")
    await db.delete(user)
    await db.commit()
