"""
WhatsApp agent — the 24/7 autonomous customer-response AI.

Flow: an inbound WhatsApp message arrives via the webhook -> we store it,
check it against the connection's escalation keywords (flagging is about
owner visibility, never about blocking the reply), then — if auto-reply is
on and the user has credits — draft a reply grounded in the business's FAQ
knowledge base (BrandProfile.docs.faq) via the Hub's dm_writer tool, send it,
and store it. No human approval step, by explicit product decision.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.hub_client import HubClient, HubError
from app.core import credits
from app.core.config import settings
from app.core.security import decrypt_secret
from app.core.user_keys import resolve_hub_key
from app.models.brand import BrandProfile
from app.models.connections import WhatsAppConnection
from app.models.user import User
from app.models.whatsapp_conversation import (
    AI,
    AWAITING_CREDITS,
    CUSTOMER,
    WhatsAppConversation,
)
from app.models.whatsapp_conversation import WhatsAppMessage
from app.services import whatsapp as wa_svc

log = logging.getLogger("uvicorn.error")

_HISTORY_LIMIT = 10  # most recent messages fed back to the Hub as context
_DRAFT_KEYS = ("message", "dm", "outreach", "draft", "full_message", "text", "content", "result")


def check_escalation(text: str, keywords_csv: str | None) -> str | None:
    """Returns the matched keyword, or None. Flagging is a visibility signal
    for the business owner — it never blocks or delays the auto-reply."""
    if not keywords_csv:
        return None
    lowered = text.lower()
    for kw in keywords_csv.split(","):
        kw = kw.strip().lower()
        if kw and kw in lowered:
            return kw
    return None


async def get_or_create_conversation(
    db: AsyncSession, user_id: int, customer_phone: str, customer_name: str | None
) -> WhatsAppConversation:
    conv = await db.scalar(
        select(WhatsAppConversation)
        .where(WhatsAppConversation.user_id == user_id)
        .where(WhatsAppConversation.customer_phone == customer_phone)
    )
    if conv is None:
        conv = WhatsAppConversation(
            user_id=user_id, customer_phone=customer_phone, customer_name=customer_name
        )
        db.add(conv)
        await db.flush()
    elif customer_name and not conv.customer_name:
        conv.customer_name = customer_name
    return conv


async def store_inbound_message(
    db: AsyncSession,
    conversation: WhatsAppConversation,
    text: str,
    meta_message_id: str | None,
    escalation_keywords: str | None,
) -> WhatsAppMessage | None:
    """Idempotent on meta_message_id — Meta can redeliver the same webhook
    event, and we must not draft/send a second reply to the same message."""
    if meta_message_id:
        existing = await db.scalar(
            select(WhatsAppMessage).where(WhatsAppMessage.meta_message_id == meta_message_id)
        )
        if existing:
            return None
    reason = check_escalation(text, escalation_keywords)
    msg = WhatsAppMessage(
        conversation_id=conversation.id,
        sender=CUSTOMER,
        text=text,
        meta_message_id=meta_message_id,
        flagged=bool(reason),
        flag_reason=reason,
    )
    db.add(msg)
    await db.flush()
    return msg


def _extract_reply(data: dict) -> str | None:
    for k in _DRAFT_KEYS:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    sequence = data.get("sequence")
    if isinstance(sequence, list):
        for step in sequence:
            if isinstance(step, dict) and isinstance(step.get("message"), str) and step["message"].strip():
                return step["message"].strip()
    return None


def _build_context(faq_entries: list[dict], history: list[WhatsAppMessage], incoming_text: str) -> str:
    parts: list[str] = []
    if faq_entries:
        parts.append(
            "Business knowledge base — answer ONLY using this information. "
            "If the question isn't covered here, say a team member will follow up soon; "
            "do not guess or make anything up."
        )
        for e in faq_entries:
            q = (e.get("question") or "").strip()
            a = (e.get("answer") or "").strip()
            if q and a:
                parts.append(f"Q: {q}\nA: {a}")
    if history:
        parts.append("Recent conversation so far:")
        for m in history:
            who = "Customer" if m.sender == CUSTOMER else "You"
            parts.append(f"{who}: {m.text}")
    parts.append(f"Customer's new message: {incoming_text}")
    return "\n\n".join(parts)


async def generate_and_send_reply(
    db: AsyncSession,
    user: User,
    conn: WhatsAppConnection,
    conversation: WhatsAppConversation,
    incoming_text: str,
) -> WhatsAppMessage | None:
    """Drafts a reply via the Hub, sends it over WhatsApp, stores it, and
    charges 1 credit on success. Returns None (no exception) if the user is
    out of credits or the connection can't send — this must never surface a
    500 to Meta's webhook caller, and never sends a placeholder "sorry" reply
    a business hasn't reviewed."""
    if not credits.has_credits(user, credits.COST_GENERATE):
        conversation.status = AWAITING_CREDITS
        await db.commit()
        log.info("WhatsApp auto-reply skipped (out of credits) for user %s", user.id)
        return None

    key = resolve_hub_key(user)
    if not key:
        log.warning("WhatsApp auto-reply skipped (no Hub key) for user %s", user.id)
        return None

    token = decrypt_secret(conn.access_token_enc)
    if not token:
        log.warning("WhatsApp auto-reply skipped (bad token) for user %s", user.id)
        return None

    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == user.id))
    faq_entries = ((brand.docs or {}).get("faq", {}).get("entries", []) if brand else []) or []
    your_role = (brand.brand_name if brand else None) or "the business"

    history_rows = await db.scalars(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conversation.id)
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(_HISTORY_LIMIT)
    )
    history = list(reversed(history_rows.all()))

    payload = {
        "prospect_name": conversation.customer_name or "the customer",
        "prospect_role": "a customer messaging your WhatsApp Business number",
        "your_role": your_role,
        "context": _build_context(faq_entries, history, incoming_text),
        "goal": "Answer the customer's question directly and helpfully — a short, natural WhatsApp reply, not a sales pitch.",
    }

    try:
        async with HubClient(settings.hub_base_url, key) as hub:
            data = await hub.call("dm_writer", payload)
    except HubError as e:
        log.warning("WhatsApp auto-reply Hub call failed for user %s: %s", user.id, e)
        return None

    reply_text = _extract_reply(data) or "Thanks for reaching out — a team member will follow up shortly."

    try:
        await wa_svc.send_text(conn.phone_number_id, token, conversation.customer_phone, reply_text)
    except Exception as e:
        log.warning("WhatsApp send failed for user %s: %s", user.id, e)
        return None

    reply_msg = WhatsAppMessage(conversation_id=conversation.id, sender=AI, text=reply_text)
    db.add(reply_msg)
    await credits.charge(db, user, credits.COST_GENERATE)
    await db.commit()
    await db.refresh(reply_msg)
    return reply_msg
