"""
Channel (Zernio) white-label helpers.

In white-label mode one app-level key serves every customer; each customer is an
isolated Zernio Profile. These helpers create/resolve that profile and list a
customer's accounts FAIL-CLOSED — only accounts whose own profileId matches the
customer's are ever returned, so a missing/forgotten scope can never leak another
customer's channels.
"""

from __future__ import annotations

from typing import Any

from app.clients.zernio_client import ZernioClient
from app.core.config import settings
from app.core.user_keys import is_white_label, resolve_zernio_key
from app.models.user import User


async def ensure_profile(user: User, db) -> str | None:
    """The customer's Zernio Profile id, creating it on first use.

    Returns None in legacy/dev mode (no app key) — callers then fall back to the
    per-user key path. In white-label mode a profile is always returned."""
    if not is_white_label():
        return None
    if user.zernio_profile_id:
        return user.zernio_profile_id
    async with ZernioClient(settings.zernio_base_url, settings.zernio_api_key) as z:
        created = await z.create_profile(
            name=f"user-{user.id}", description=user.email or f"user {user.id}"
        )
    pid = created.get("_id") or created.get("id")
    if pid:
        user.zernio_profile_id = str(pid)
        await db.commit()
    return user.zernio_profile_id


def _account_profile_id(acc: dict) -> str | None:
    """Zernio returns profileId as either a string or an embedded {_id,...}."""
    p = acc.get("profileId")
    if isinstance(p, dict):
        return p.get("_id") or p.get("id")
    return p if isinstance(p, str) else None


async def list_customer_accounts(user: User, db) -> list[dict[str, Any]]:
    """Accounts for THIS customer only — fail-closed.

    White-label: scope the request to the customer's profile AND defensively drop
    any account whose own profileId doesn't match (belt and suspenders). If we
    can't establish the customer's profile, return nothing rather than risk a leak.
    """
    key = resolve_zernio_key(user)
    if not key:
        return []
    if is_white_label():
        pid = await ensure_profile(user, db)
        if not pid:
            return []
        async with ZernioClient(settings.zernio_base_url, key) as z:
            data = await z.list_accounts(profile_id=pid)
        accts = data.get("accounts") or data.get("data") or []
        # FAIL-CLOSED: only accounts that truly belong to this customer's profile.
        return [a for a in accts if _account_profile_id(a) == pid]
    # Legacy/dev single-tenant: the per-user key already scopes to that user.
    async with ZernioClient(settings.zernio_base_url, key) as z:
        data = await z.list_accounts()
    return data.get("accounts") or data.get("data") or []
