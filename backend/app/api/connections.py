"""
Channel connections API — WhatsApp Business and Telegram.

Each user can connect one of each. Credentials are stored encrypted.
Auto-post toggles let users choose per-channel whether published posts
are automatically cross-posted.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret, require_feature
from app.db.session import get_db
from app.models.connections import TelegramConnection, WhatsAppConnection
from app.models.user import User
from app.models.whatsapp_conversation import WhatsAppConversation, WhatsAppMessage
from app.services import telegram as tg_svc
from app.services import whatsapp as wa_svc

router = APIRouter(prefix="/connections", tags=["connections"])

# Sensible starting point; user-editable via PATCH /whatsapp/agent.
DEFAULT_ESCALATION_KEYWORDS = (
    "refund, chargeback, cancel, complaint, legal, lawsuit, scam, fraud, "
    "credit card, bank details"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wa_out(conn: WhatsAppConnection | None) -> dict:
    if not conn:
        return {"connected": False, "auto_post": False, "auto_reply_enabled": False}
    base = (settings.app_base_url or "").rstrip("/")
    return {
        "connected": True,
        "phone_number_id": conn.phone_number_id,
        "display_phone": conn.display_phone,
        "verified_name": conn.verified_name,
        "to_number": conn.to_number,
        "auto_post": conn.auto_post,
        "auto_reply_enabled": conn.auto_reply_enabled,
        "escalation_keywords": conn.escalation_keywords or DEFAULT_ESCALATION_KEYWORDS,
        "webhook_url": f"{base}/api/whatsapp/webhook" if base else None,
        "webhook_verify_token": conn.webhook_verify_token,
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
    app_secret: str | None = Field(
        None, description="Meta App Settings > Basic > App Secret — required for the WhatsApp agent's webhook signature verification."
    )


@router.post("/whatsapp")
@require_feature("whatsapp_agent")
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
    if body.app_secret:
        conn.app_secret_enc = encrypt_secret(body.app_secret)
    # Generated once, not rotated on reconnect — rotating would silently break
    # an already-configured Meta webhook until the user re-pastes the token.
    if not conn.webhook_verify_token:
        conn.webhook_verify_token = secrets.token_urlsafe(24)
    if not conn.escalation_keywords:
        conn.escalation_keywords = DEFAULT_ESCALATION_KEYWORDS
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
@require_feature("whatsapp_agent")
async def disconnect_whatsapp(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conn = await _get_wa(current.id, db)
    if conn:
        await db.delete(conn)
        await db.commit()


@router.patch("/whatsapp/toggle")
@require_feature("whatsapp_agent")
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
@require_feature("whatsapp_agent")
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


# ── WhatsApp agent (24/7 autonomous customer-response AI) ──────────────────────

class WhatsAppAgentSettings(BaseModel):
    auto_reply_enabled: bool | None = None
    escalation_keywords: str | None = None


@router.patch("/whatsapp/agent")
@require_feature("whatsapp_agent")
async def update_whatsapp_agent_settings(
    body: WhatsAppAgentSettings,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conn = await _get_wa(current.id, db)
    if not conn:
        raise HTTPException(404, "WhatsApp not connected.")
    if body.auto_reply_enabled is not None:
        conn.auto_reply_enabled = body.auto_reply_enabled
    if body.escalation_keywords is not None:
        conn.escalation_keywords = body.escalation_keywords
    await db.commit()
    await db.refresh(conn)
    return _wa_out(conn)


@router.get("/whatsapp/agent")
@require_feature("whatsapp_agent")
async def get_whatsapp_agent_settings(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Connection + agent settings, plus whether the webhook has ever
    actually received a message — the single most useful signal for a user
    debugging "why isn't my AI replying," since a misconfigured Meta webhook
    fails silently otherwise."""
    conn = await _get_wa(current.id, db)
    out = _wa_out(conn)
    if conn:
        received = await db.scalar(
            select(func.count(WhatsAppMessage.id))
            .join(WhatsAppConversation, WhatsAppMessage.conversation_id == WhatsAppConversation.id)
            .where(WhatsAppConversation.user_id == current.id)
            .where(WhatsAppMessage.sender == "customer")
        )
        out["webhook_active"] = bool(received)
    return out


def _conversation_out(conv: WhatsAppConversation) -> dict:
    return {
        "id": conv.id,
        "customer_phone": conv.customer_phone,
        "customer_name": conv.customer_name,
        "status": conv.status,
        "updated_at": conv.updated_at,
    }


def _message_out(msg: WhatsAppMessage) -> dict:
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender": msg.sender,
        "text": msg.text,
        "flagged": msg.flagged,
        "flag_reason": msg.flag_reason,
        "created_at": msg.created_at,
    }


@router.get("/whatsapp/flagged")
@require_feature("whatsapp_agent")
async def list_flagged_whatsapp_messages(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Flagged customer messages needing a human's eyes — plus the AI's reply
    that followed, if any, so the owner can see what was actually sent."""
    rows = await db.execute(
        select(WhatsAppMessage, WhatsAppConversation)
        .join(WhatsAppConversation, WhatsAppMessage.conversation_id == WhatsAppConversation.id)
        .where(WhatsAppConversation.user_id == current.id)
        .where(WhatsAppMessage.flagged.is_(True))
        .order_by(WhatsAppMessage.created_at.desc())
    )
    out = []
    for msg, conv in rows.all():
        # id, not created_at, breaks ties correctly — the inbound message and
        # its AI reply are often stored within the same second.
        reply = await db.scalar(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.conversation_id == conv.id)
            .where(WhatsAppMessage.sender == "ai")
            .where(WhatsAppMessage.id > msg.id)
            .order_by(WhatsAppMessage.id.asc())
            .limit(1)
        )
        out.append({
            "message": _message_out(msg),
            "conversation": _conversation_out(conv),
            "ai_reply": _message_out(reply) if reply else None,
        })
    return out


@router.post("/whatsapp/flagged/{message_id}/dismiss")
@require_feature("whatsapp_agent")
async def dismiss_flagged_whatsapp_message(
    message_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    msg = await db.scalar(
        select(WhatsAppMessage)
        .join(WhatsAppConversation, WhatsAppMessage.conversation_id == WhatsAppConversation.id)
        .where(WhatsAppMessage.id == message_id)
        .where(WhatsAppConversation.user_id == current.id)
    )
    if not msg:
        raise HTTPException(404, "Flagged message not found.")
    msg.flagged = False
    await db.commit()
    return {"ok": True}


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
