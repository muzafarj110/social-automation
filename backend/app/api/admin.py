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
        "resend_api_key_set": bool(settings.resend_api_key),
        "resend_from": settings.resend_from,
        "app_base_url": settings.app_base_url or "(not set — links will be broken)",
    }


@router.post("/test-email")
async def test_email(current: User = Depends(require_admin)) -> dict:
    """Send a test email to the admin via Resend. Returns ok + any error detail."""
    if not settings.email_enabled:
        return {
            "ok": False,
            "error": "Email is disabled — set RESEND_API_KEY in Railway.",
        }
    import httpx
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from,
                    "to": [current.email],
                    "subject": "Autopilot — test email",
                    "html": "<p>This is a test email from Autopilot. Email delivery is working!</p>",
                },
            )
        if r.status_code >= 400:
            error = f"Resend API error {r.status_code}: {r.text[:300]}"
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
