"""
WhatsApp Business and Telegram channel connections.

Each user can have one of each. Tokens are stored encrypted via Fernet
(same mechanism as hub_api_key_enc on the User model).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.db.base import Base


class WhatsAppConnection(Base):
    __tablename__ = "whatsapp_connections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    # Meta Cloud API credentials
    phone_number_id = Column(String, nullable=False)
    access_token_enc = Column(String, nullable=False)  # encrypted permanent token
    # Display info fetched from Meta on connect
    display_phone = Column(String, nullable=True)
    verified_name = Column(String, nullable=True)
    # Default send-to number (E.164 format, e.g. +15550001234)
    to_number = Column(String, nullable=True)
    auto_post = Column(Boolean, nullable=False, default=False)
    # WhatsApp agent — 24/7 autonomous customer-response AI (separate from
    # auto_post, which is the unrelated/unbuilt "cross-post my LinkedIn
    # content" toggle above).
    auto_reply_enabled = Column(Boolean, nullable=False, default=False)
    escalation_keywords = Column(String, nullable=True)  # comma-separated
    webhook_verify_token = Column(String, nullable=True)  # generated on connect
    # Meta App Secret (App Settings > Basic — different from the access
    # token) used to verify the X-Hub-Signature-256 header on inbound
    # webhook calls, so a third party can't forge customer messages that
    # trigger real AI replies and spend real credits under this business's
    # identity.
    app_secret_enc = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class TelegramConnection(Base):
    __tablename__ = "telegram_connections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    # Bot credentials from @BotFather
    bot_token_enc = Column(String, nullable=False)  # encrypted
    bot_username = Column(String, nullable=True)  # e.g. "@MyBrandBot"
    # Channel / group to post to (optional — can also DM)
    channel_id = Column(String, nullable=True)  # "@channel" or "-100xxxxxxxxxx"
    auto_post = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
