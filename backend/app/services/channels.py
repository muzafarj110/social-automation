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

from app.clients.zernio_client import ZernioClient, ZernioError
from app.core.config import settings
from app.core.user_keys import is_white_label, resolve_zernio_key
from app.models.user import User


def _find_profile_id(profiles_resp: dict, name: str) -> str | None:
    plist = profiles_resp.get("profiles") or profiles_resp.get("data") or []
    if not isinstance(plist, list):
        return None
    for p in plist:
        if isinstance(p, dict) and p.get("name") == name:
            return p.get("_id") or p.get("id")
    return None


async def ensure_profile(user: User, db) -> str | None:
    """The customer's Zernio Profile id — idempotent find-or-create.

    Returns None in legacy/dev mode (no app key), or if we can't establish the
    profile (callers then fail closed). Never raises into the endpoint: any Zernio
    error is swallowed and surfaced as "no profile yet". The profile name is
    derived from the user id, so it's stable across calls and recoverable if our
    stored id was lost.
    """
    if not is_white_label():
        return None
    if user.zernio_profile_id:
        return user.zernio_profile_id

    name = f"user-{user.id}"
    pid: str | None = None
    try:
        async with ZernioClient(settings.zernio_base_url, settings.zernio_api_key) as z:
            # 1) reuse an existing profile with our name (avoids duplicate-name errors)
            try:
                pid = _find_profile_id(await z.list_profiles(), name)
            except ZernioError:
                pid = None
            # 2) otherwise create it; if it races/already-exists, re-list and find it
            if not pid:
                try:
                    created = await z.create_profile(name=name, description=user.email or name)
                    pid = created.get("_id") or created.get("id")
                except ZernioError:
                    try:
                        pid = _find_profile_id(await z.list_profiles(), name)
                    except ZernioError:
                        pid = None
    except Exception:  # network/transport — fail closed, never 500 the endpoint
        return user.zernio_profile_id

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
