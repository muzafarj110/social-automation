"""
Telegram Bot API client.

Free, unlimited messages. Users create a bot via @BotFather and add it
as an admin to their channel.
Docs: https://core.telegram.org/bots/api
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException

_BASE = "https://api.telegram.org"
_TIMEOUT = 15


def _bot_url(token: str, method: str) -> str:
    return f"{_BASE}/bot{token}/{method}"


async def get_bot_info(token: str) -> dict:
    """Validate token and fetch bot username via getMe."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(_bot_url(token, "getMe"))
    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(400, "Telegram token is invalid. Check @BotFather and try again.")
    return data.get("result", {})


async def send_message(token: str, chat_id: str, text: str) -> dict:
    """Send a text message to a chat/channel/group."""
    payload = {
        "chat_id": chat_id,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(_bot_url(token, "sendMessage"), json=payload)
    data = resp.json()
    if not data.get("ok"):
        desc = data.get("description", "unknown error")
        raise HTTPException(502, f"Telegram send failed: {desc}")
    return data
