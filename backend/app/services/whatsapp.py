"""
Meta WhatsApp Business Cloud API client.

Free tier: 1,000 service conversations/month.
Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException

_API_VERSION = "v19.0"
_BASE = f"https://graph.facebook.com/{_API_VERSION}"
_TIMEOUT = 15


async def get_phone_info(phone_number_id: str, token: str) -> dict:
    """Fetch display_phone_number and verified_name from Meta."""
    url = f"{_BASE}/{phone_number_id}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": "display_phone_number,verified_name"},
        )
    if resp.status_code == 401:
        raise HTTPException(400, "WhatsApp token is invalid or expired.")
    if not resp.is_success:
        raise HTTPException(502, f"Meta API error: {resp.text[:200]}")
    return resp.json()


async def send_text(
    phone_number_id: str,
    token: str,
    to: str,
    text: str,
) -> dict:
    """Send a text message via WhatsApp Cloud API."""
    url = f"{_BASE}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text[:4096]},
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if resp.status_code == 401:
        raise HTTPException(400, "WhatsApp token is invalid. Reconnect your account.")
    if not resp.is_success:
        detail = resp.json().get("error", {}).get("message", resp.text[:200])
        raise HTTPException(502, f"WhatsApp send failed: {detail}")
    return resp.json()
