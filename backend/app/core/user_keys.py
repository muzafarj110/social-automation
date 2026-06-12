"""Resolve per-user external API keys (decrypted at use time)."""

from __future__ import annotations

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.user import User


def resolve_zernio_key(user: User) -> str | None:
    """The user's own Zernio key, or None if they haven't set one.

    No app-level fallback: isolation depends on each user acting only through
    their own Zernio connection.
    """
    if user.zernio_api_key_enc:
        return decrypt_secret(user.zernio_api_key_enc)
    return None


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
