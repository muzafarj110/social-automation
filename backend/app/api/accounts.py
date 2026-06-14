"""Account linking routes — attach Zernio-connected LinkedIn accounts to a user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.zernio_client import ZernioClient, ZernioError
from app.core import platforms as plat
from app.core.config import settings
from app.core.user_keys import resolve_zernio_key
from app.db.session import get_db
from app.models.account import LinkedInAccount
from app.models.user import User
from app.schemas.account import AccountOut, ConnectRequest, LinkAccountRequest

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/platforms")
async def supported_platforms() -> dict[str, object]:
    """The platforms the app can post to (for UI pickers)."""
    return {
        "platforms": [
            {"value": k, "label": v["label"],
             "supports_hashtags": v["supports_hashtags"],
             "char_limit": v["char_limit"], "media_required": v["media_required"]}
            for k, v in plat.PLATFORMS.items()
        ]
    }


@router.get("/zernio/available")
async def zernio_available_accounts(
    current: User = Depends(get_current_user),
) -> dict[str, object]:
    """List LinkedIn accounts under THIS user's own Zernio key, so they can find
    the accountId to link. Each user only sees their own Zernio connection."""
    key = resolve_zernio_key(current)
    if not key:
        raise HTTPException(400, "Connect your channels first.")
    async with ZernioClient(settings.zernio_base_url, key) as z:
        try:
            return await z.list_accounts()
        except ZernioError as e:
            raise HTTPException(e.status_code or 502, e.message) from e


@router.post("/connect-url")
async def connect_url(
    body: ConnectRequest,
    current: User = Depends(get_current_user),
) -> dict[str, object]:
    """Start an in-app OAuth connect for a platform via Zernio's hosted flow.

    Returns an authUrl the frontend opens in a new tab. After the user
    authorizes, the account is connected under their Zernio profile — they then
    import it here. No social-account credential ever passes through our app.
    """
    key = resolve_zernio_key(current)
    if not key:
        raise HTTPException(400, "Connect your channels first.")
    platform = plat.normalize(body.platform)
    async with ZernioClient(settings.zernio_base_url, key) as z:
        try:
            profs = await z.list_profiles()
            plist = profs.get("profiles") or profs.get("data") or []
            if isinstance(plist, list) and plist:
                first = plist[0]
                profile_id = first.get("_id") or first.get("id")
            else:
                created = await z.create_profile(name="Autopilot")
                profile_id = created.get("_id") or created.get("id")
            res = await z.get_connect_url(platform=platform, profile_id=str(profile_id))
        except ZernioError as e:
            raise HTTPException(e.status_code or 502, e.message) from e
    auth_url = res.get("authUrl") or res.get("auth_url") or res.get("url")
    if not auth_url:
        raise HTTPException(502, "Couldn't start the connection — please try again.")
    return {"ok": True, "auth_url": auth_url}


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LinkedInAccount]:
    rows = await db.scalars(
        select(LinkedInAccount).where(LinkedInAccount.user_id == current.id)
    )
    return list(rows)


@router.post("/link", response_model=AccountOut, status_code=201)
async def link_account(
    body: LinkAccountRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkedInAccount:
    existing = await db.scalar(
        select(LinkedInAccount).where(
            LinkedInAccount.user_id == current.id,
            LinkedInAccount.zernio_account_id == body.zernio_account_id,
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already linked")

    account = LinkedInAccount(
        user_id=current.id,
        platform=plat.normalize(body.platform),
        zernio_account_id=body.zernio_account_id,
        account_type=body.account_type,
        display_name=body.display_name,
        avatar_url=body.avatar_url,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204, response_model=None)
async def unlink_account(
    account_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    account = await db.get(LinkedInAccount, account_id)
    if not account or account.user_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    await db.delete(account)
    await db.commit()
