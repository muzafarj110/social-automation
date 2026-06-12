"""Resolve per-user external API keys (decrypted at use time)."""

from __future__ import annotations

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
