"""
Approvals service — drafting (Hub) and compliant execution (Zernio) for the
human-in-the-loop inbox.

- Drafting: call the Hub endpoint for the approval's `kind`, return the full
  payload plus a best-effort editable text the user reviews.
- Execution: only company-page comment replies have a compliant Zernio path
  (POST /comments/{id}/reply). Everything else is marked ready for the human to
  send/apply manually (LinkedIn exposes no official API for it).
"""

from __future__ import annotations

import json
from typing import Any

from app.clients.hub_client import HubClient
from app.clients.zernio_client import ZernioClient
from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.user import User

# approval.kind -> Hub endpoint registry name (see hub_client.ENDPOINTS)
KIND_TO_HUB: dict[str, str] = {
    "comment": "comment_writer",
    "dm": "dm_writer",
    "outreach": "outreach_campaign",
    "profile": "profile_optimizer",
}

# Best-effort keys to pull human-editable text from each draft, in priority order.
_TEXT_KEYS: dict[str, tuple[str, ...]] = {
    "comment": ("comment", "full_comment", "comment_text", "text", "reply"),
    "dm": ("message", "full_message", "dm", "text", "body"),
    "outreach": ("first_message", "opener", "message", "sequence", "steps", "text"),
    "profile": ("about", "optimized_about", "summary", "headline", "text"),
}


class DraftError(Exception):
    """Drafting cannot proceed (config) — mapped to HTTP in the router."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def resolve_hub_key(user: User) -> str:
    if user.hub_api_key_enc:
        key = decrypt_secret(user.hub_api_key_enc)
        if key:
            return key
    if settings.hub_api_key and not settings.hub_api_key.startswith("paste-"):
        return settings.hub_api_key
    raise DraftError(
        "No Hub API key on file. Set one via PUT /api/auth/me/hub-key.", status_code=400
    )


def extract_draft_text(kind: str, data: dict[str, Any]) -> str:
    """Pull a sensible editable string out of a Hub draft payload."""
    for key in _TEXT_KEYS.get(kind, ()):  # known candidates first
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list) and val:  # e.g. outreach steps
            first = val[0]
            if isinstance(first, str):
                return first.strip()
            if isinstance(first, dict):
                for k in ("message", "text", "body"):
                    if isinstance(first.get(k), str):
                        return first[k].strip()
    # Fallback: first non-empty top-level string value (ignore bookkeeping keys).
    for k, v in data.items():
        if k.startswith("_"):
            continue
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Last resort: compact JSON so the user still has something to edit.
    return json.dumps({k: v for k, v in data.items() if not k.startswith("_")})


async def generate_draft(
    user: User, kind: str, params: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """Call the Hub for `kind`; return (full_payload, editable_text)."""
    endpoint_name = KIND_TO_HUB[kind]
    key = resolve_hub_key(user)
    async with HubClient(settings.hub_base_url, key) as hub:
        data = await hub.call(endpoint_name, params)
    return data, extract_draft_text(kind, data)


async def reply_company_comment(
    comment_id: str, message: str, *, zernio_key: str
) -> dict[str, Any]:
    """Execute a company-page comment reply via the user's own Zernio key."""
    if not zernio_key:
        raise DraftError("Set your Zernio API key in the app first.", status_code=400)
    async with ZernioClient(settings.zernio_base_url, zernio_key) as z:
        return await z.reply_comment(comment_id, message)
