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
    """Return current email config status so admin can debug delivery issues."""
    active = "smtp" if settings.smtp_enabled else ("resend" if settings.resend_enabled else "none")
    return {
        "email_enabled": settings.email_enabled,
        "active_provider": active,
        # SMTP
        "smtp_enabled": settings.smtp_enabled,
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user or "(not set)",
        "smtp_pass_set": bool(settings.smtp_pass),
        "smtp_from": settings.smtp_from or (f"Autopilot <{settings.smtp_user}>" if settings.smtp_user else "(not set)"),
        # Resend fallback
        "resend_enabled": settings.resend_enabled,
        "resend_api_key_set": bool(settings.resend_api_key),
        "resend_from": settings.resend_from,
        # Links
        "app_base_url": settings.app_base_url or "(not set — links will be broken)",
    }


class TestEmailBody(BaseModel):
    to: str = ""
    include_verify_link: bool = False


@router.post("/test-email")
async def test_email(
    body: TestEmailBody = TestEmailBody(),
    current: User = Depends(require_admin),
) -> dict:
    """Send a diagnostic test email via Resend. Accepts optional target address."""
    if not settings.email_enabled:
        return {"ok": False, "error": "Email disabled — RESEND_API_KEY not set in Railway."}

    target = body.to.strip() or current.email
    base = (settings.app_base_url or "").rstrip("/")
    app_base_warn = "(not set — links will be broken!)" if not base else base

    html = f"""
    <div style='font-family:system-ui,sans-serif;max-width:480px'>
      <h2>Autopilot — email delivery test</h2>
      <p>If you received this, Resend can deliver to <b>{target}</b>.</p>
      <hr style='border:none;border-top:1px solid #e5e7eb;margin:16px 0'>
      <p style='font-size:13px;color:#666'><b>APP_BASE_URL:</b> {app_base_warn}</p>
      <p style='font-size:13px;color:#666'>{'<b style="color:red">⚠ APP_BASE_URL is missing — verify/reset links in real emails will be broken.</b>' if not base else '✓ APP_BASE_URL is set correctly.'}</p>
      {'<p><a href="' + base + '/#verify?token=SAMPLE_TOKEN" style="display:inline-block;background:#0d9488;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none">Sample verify link (click to test)</a></p>' if body.include_verify_link and base else ''}
    </div>
    """

    import smtplib, ssl, asyncio
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    provider = "SMTP" if settings.smtp_enabled else "Resend"
    error: str | None = None

    if settings.smtp_enabled:
        def _try_smtp():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Autopilot — email test"
            msg["From"] = settings.smtp_from or f"Autopilot <{settings.smtp_user}>"
            msg["To"] = target
            msg.attach(MIMEText(html, "html"))
            ctx = ssl.create_default_context()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.login(settings.smtp_user, settings.smtp_pass)
                s.sendmail(msg["From"], [target], msg.as_string())
        try:
            await asyncio.to_thread(_try_smtp)
        except smtplib.SMTPAuthenticationError as e:
            raw = e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else str(e)
            error = f"Gmail auth failed: {raw} — SMTP_PASS must be a 16-char App Password, not your Gmail login password."
        except smtplib.SMTPException as e:
            error = f"SMTP error: {e}"
        except Exception as e:
            error = f"Connection error: {e}"
    else:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                    json={"from": settings.resend_from, "to": [target], "subject": "Autopilot — email test", "html": html},
                )
            if r.status_code >= 400:
                error = f"Resend error {r.status_code}: {r.text[:300]}"
        except Exception as e:
            error = f"Resend connection error: {e}"

    if error:
        return {"ok": False, "error": error, "sent_to": target, "provider": provider}
    return {
        "ok": True, "sent_to": target, "provider": provider,
        "app_base_url": base or "(not set)",
        "message": f"Sent via {provider} to {target}. Check inbox + spam.",
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


@router.delete("/users/{user_id}", status_code=204)
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
