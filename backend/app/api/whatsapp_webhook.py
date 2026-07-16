"""
WhatsApp agent webhook — Meta calls this for every inbound message.

One shared endpoint for every business using this SaaS (each connects their
own Meta Developer App and points its webhook here). The payload's
`metadata.phone_number_id` identifies which WhatsAppConnection — and thus
which user — a message belongs to.

GET  — Meta's one-time verification handshake when the webhook URL is saved
       in the Meta dashboard.
POST — actual message delivery. Verified via X-Hub-Signature-256 (HMAC-SHA256
       over the raw body, keyed by the connection's Meta App Secret) before
       anything is trusted — this is a public, unauthenticated endpoint, and
       without it anyone could forge "customer" messages that trigger real
       AI replies and spend real credits under a business's identity.

Always returns 200 quickly (Meta retries aggressively on non-2xx); reply
generation happens in a background task after the response is sent.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response
from sqlalchemy import select

from app.core.security import decrypt_secret
from app.db.session import SessionLocal
from app.models.connections import WhatsAppConnection
from app.models.user import User
from app.services import whatsapp_conversations as wa_conv

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhook"])
log = logging.getLogger("uvicorn.error")


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> Response:
    if hub_mode != "subscribe" or not hub_verify_token:
        return Response(status_code=403)
    async with SessionLocal() as db:
        conn = await db.scalar(
            select(WhatsAppConnection).where(WhatsAppConnection.webhook_verify_token == hub_verify_token)
        )
    if not conn:
        return Response(status_code=403)
    return Response(content=hub_challenge or "", media_type="text/plain")


def _verify_signature(body: bytes, header_sig: str | None, app_secret: str) -> bool:
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig.removeprefix("sha256="))


async def _process_message(
    user_id: int, phone_number_id: str, from_number: str, text: str,
    meta_message_id: str | None, customer_name: str | None,
) -> None:
    """Runs after the webhook response is already sent — stores the message,
    flags it if needed, and (if enabled) generates + sends the AI reply."""
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        conn = await db.scalar(
            select(WhatsAppConnection).where(WhatsAppConnection.phone_number_id == phone_number_id)
        )
        if not user or not conn:
            return
        conversation = await wa_conv.get_or_create_conversation(db, user_id, from_number, customer_name)
        msg = await wa_conv.store_inbound_message(
            db, conversation, text, meta_message_id, conn.escalation_keywords
        )
        await db.commit()
        if msg is None:
            return  # duplicate delivery (Meta retry) — already handled
        if conn.auto_reply_enabled:
            await wa_conv.generate_and_send_reply(db, user, conn, conversation, text)


@router.post("/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks) -> dict:
    body = await request.body()

    try:
        payload = await request.json()
    except Exception:
        return {"received": True}  # malformed body — nothing to do, ack anyway

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
            if not phone_number_id:
                continue

            async with SessionLocal() as db:
                conn = await db.scalar(
                    select(WhatsAppConnection).where(WhatsAppConnection.phone_number_id == phone_number_id)
                )
            if not conn:
                log.warning("WhatsApp webhook: no connection for phone_number_id %s", phone_number_id)
                continue

            app_secret = decrypt_secret(conn.app_secret_enc) if conn.app_secret_enc else None
            if not app_secret:
                log.warning("WhatsApp webhook: no app secret configured for connection %s — rejecting", conn.id)
                continue
            sig = request.headers.get("x-hub-signature-256")
            if not _verify_signature(body, sig, app_secret):
                log.warning("WhatsApp webhook: signature verification failed for connection %s", conn.id)
                continue

            contacts = {c.get("wa_id"): c for c in value.get("contacts", []) if isinstance(c, dict)}
            for m in value.get("messages", []):
                if m.get("type") != "text":
                    continue  # MVP: text messages only
                from_number = m.get("from")
                text = (m.get("text") or {}).get("body")
                if not from_number or not text:
                    continue
                contact = contacts.get(from_number, {})
                customer_name = (contact.get("profile") or {}).get("name")
                background.add_task(
                    _process_message,
                    conn.user_id, phone_number_id, from_number, text,
                    m.get("id"), customer_name,
                )

    return {"received": True}
