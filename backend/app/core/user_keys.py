"""Resolve per-user external API keys (decrypted at use time)."""

from __future__ import annotations

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.user import User


def resolve_zernio_key(user: User) -> str | None:
    """The connection key used to reach the channel provider.

    White-label: the app-level key is authoritative — every customer's channels
    live under it, isolated by their own Zernio Profile (see `ensure_profile`),
    and every read is profile-scoped + fail-closed. Falls back to a per-user key
    only when no app key is configured (e.g. local dev), which is single-tenant
    anyway. Customers never enter a key.
    """
    if settings.zernio_api_key and not settings.zernio_api_key.startswith("paste-"):
        return settings.zernio_api_key
    if user.zernio_api_key_enc:
        return decrypt_secret(user.zernio_api_key_enc)
    return None


def is_white_label() -> bool:
    """True when an app-level channel key is configured (multi-tenant mode)."""
    return bool(settings.zernio_api_key) and not settings.zernio_api_key.startswith("paste-")


def resolve_hub_key(user: User) -> str | None:
    """The user's own Hub key, falling back to the app-level key in dev.

    The Hub is the content brain (not an action surface), so a shared fallback
    is acceptable here — unlike Zernio, which gates account access.
    """
    if user.hub_api_key_enc:
        key = decrypt_secret(user.hub_api_key_enc)
        if key:
            return key
    if settings.hub_api_key and not settings.hub_api_key.startswith("paste-"):
        return settings.hub_api_key
    return None
