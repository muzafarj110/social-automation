"""
Channel connections API — WhatsApp Business and Telegram.

Each user can connect one of each. Credentials are stored encrypted.
Auto-post toggles let users choose per-channel whether published posts
are automatically cross-posted.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import decrypt_secret, encrypt_secret
from app.db.session import get_db
from app.models.connections import TelegramConnection, WhatsAppConnection
from app.models.user import User
from app.services import telegram as tg_svc
from app.services import whatsapp as wa_svc

router = APIRouter(prefix="/connections", tags=["connections"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wa_out(conn: WhatsAppConnection | None) -> dict:
    if not conn:
        return {"connected": False, "auto_post": False}
    return {
        "connected": True,
        "phone_number_id": conn.phone_number_id,
        "display_phone": conn.display_phone,
        "verified_name": conn.verified_name,
        "to_number": conn.to_number,
        "auto_post": conn.auto_post,
    }


def _tg_out(conn: TelegramConnection | None) -> dict:
    if not conn:
        return {"connected": False, "auto_post": False}
    return {
        "connected": True,
        "bot_username": conn.bot_username,
        "channel_id": conn.channel_id,
        "auto_post": conn.auto_post,
    }


async def _get_wa(user_id: int, db: AsyncSession) -> WhatsAppConnection | None:
    return await db.scalar(
        select(WhatsAppConnection).where(WhatsAppConnection.user_id == user_id)
    )


async def _get_tg(user_id: int, db: AsyncSession) -> TelegramConnection | None:
    return await db.scalar(
        select(TelegramConnection).where(TelegramConnection.user_id == user_id)
    )


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("")
async def get_connections(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    wa = await _get_wa(current.id, db)
    tg = await _get_tg(current.id, db)
    return {"whatsapp": _wa_out(wa), "telegram": _tg_out(tg)}


# ── WhatsApp ──────────────────────────────────────────────────────────────────

class WhatsAppConnect(BaseModel):
    phone_number_id: str = Field(..., min_length=1)
    access_token: str = Field(..., min_length=1)
    to_number: str = Field(..., min_length=1, description="E.164 format, e.g. +15550001234")


@router.post("/whatsapp")
async def connect_whatsapp(
    body: WhatsAppConnect,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save WhatsApp Business credentials and verify with Meta."""
    info = await wa_svc.get_phone_info(body.phone_number_id, body.access_token)

    conn = await _get_wa(current.id, db)
    if conn is None:
        conn = WhatsAppConnection(user_id=current.id)
        db.add(conn)

    conn.phone_number_id = body.phone_number_id
    conn.access_token_enc = encrypt_secret(body.access_token)
    conn.to_number = body.to_number
    conn.display_phone = info.get("display_phone_number")
    conn.verified_name = info.get("verified_name")
    await db.commit()
    await db.refresh(conn)

    # Send a welcome test message so users know it's working.
    try:
        await wa_svc.send_text(
            body.phone_number_id,
            body.access_token,
            body.to_number,
            "✅ Autopilot connected! Your WhatsApp Business account is now linked. "
            "Toggle auto-post to cross-post your LinkedIn content here automatically.",
        )
    except Exception:
        pass  # connection saved; test message failure is non-fatal

    return _wa_out(conn)


@router.delete("/whatsapp", status_code=204, response_model=None)
async def disconnect_whatsapp(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conn = await _get_wa(current.id, db)
    if conn:
        await db.delete(conn)
        await db.commit()


@router.patch("/whatsapp/toggle")
async def toggle_whatsapp_autopost(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conn = await _get_wa(current.id, db)
    if not conn:
        raise HTTPException(404, "WhatsApp not connected.")
    conn.auto_post = not conn.auto_post
    await db.commit()
    return {"auto_post": conn.auto_post}


class WASendRequest(BaseModel):
    text: str = Field(..., min_length=1)
    to_number: str | None = None


@router.post("/whatsapp/send")
async def send_whatsapp(
    body: WASendRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually send a message via WhatsApp."""
    conn = await _get_wa(current.id, db)
    if not conn:
        raise HTTPException(404, "WhatsApp not connected.")
    token = decrypt_secret(conn.access_token_enc)
    if not token:
        raise HTTPException(400, "WhatsApp token could not be decrypted. Reconnect your account.")
    to = body.to_number or conn.to_number
    if not to:
        raise HTTPException(400, "No recipient number configured.")
    result = await wa_svc.send_text(conn.phone_number_id, token, to, body.text)
    return {"ok": True, "result": result}


# ── Telegram ──────────────────────────────────────────────────────────────────

class TelegramConnect(BaseModel):
    bot_token: str = Field(..., min_length=1)
    channel_id: str | None = None


@router.post("/telegram")
async def connect_telegram(
    body: TelegramConnect,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save Telegram bot token and verify with Telegram API."""
    info = await tg_svc.get_bot_info(body.bot_token)

    conn = await _get_tg(current.id, db)
    if conn is None:
        conn = TelegramConnection(user_id=current.id)
        db.add(conn)

    conn.bot_token_enc = encrypt_secret(body.bot_token)
    conn.bot_username = "@" + info.get("username", "")
    conn.channel_id = body.channel_id or None
    await db.commit()
    await db.refresh(conn)

    # Send a welcome test message if channel is configured.
    if body.channel_id:
        try:
            await tg_svc.send_message(
                body.bot_token,
                body.channel_id,
                "✅ <b>Autopilot connected!</b>\n\nYour Telegram channel is now linked. "
                "Toggle auto-post to cross-post your LinkedIn content here automatically.",
            )
        except Exception:
            pass

    return _tg_out(conn)


@router.delete("/telegram", status_code=204, response_model=None)
async def disconnect_telegram(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conn = await _get_tg(current.id, db)
    if conn:
        await db.delete(conn)
        await db.commit()


@router.patch("/telegram/toggle")
async def toggle_telegram_autopost(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conn = await _get_tg(current.id, db)
    if not conn:
        raise HTTPException(404, "Telegram not connected.")
    conn.auto_post = not conn.auto_post
    await db.commit()
    return {"auto_post": conn.auto_post}


class TGSendRequest(BaseModel):
    text: str = Field(..., min_length=1)
    channel_id: str | None = None


@router.post("/telegram/send")
async def send_telegram(
    body: TGSendRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually send a message via Telegram."""
    conn = await _get_tg(current.id, db)
    if not conn:
        raise HTTPException(404, "Telegram not connected.")
    token = decrypt_secret(conn.bot_token_enc)
    if not token:
        raise HTTPException(400, "Telegram token could not be decrypted. Reconnect your account.")
    chat = body.channel_id or conn.channel_id
    if not chat:
        raise HTTPException(400, "No channel configured.")
    result = await tg_svc.send_message(token, chat, body.text)
    return {"ok": True, "result": result}
