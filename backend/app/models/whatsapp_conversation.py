"""WhatsApp agent — conversation + message storage for the 24/7 autonomous
customer-response AI. One conversation per (user, customer phone number);
messages are the full back-and-forth thread, both inbound (customer) and
outbound (AI-generated) sides."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ACTIVE = "active"
RESOLVED = "resolved"
AWAITING_CREDITS = "awaiting_credits"

CUSTOMER = "customer"
AI = "ai"


class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        UniqueConstraint("user_id", "customer_phone", name="uq_whatsapp_conv_user_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    customer_phone: Mapped[str] = mapped_column(String(32), index=True)  # E.164
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ACTIVE, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), index=True
    )
    sender: Mapped[str] = mapped_column(String(10))  # "customer" | "ai"
    text: Mapped[str] = mapped_column(Text)
    # Meta's own message id, for webhook-redelivery idempotency.
    meta_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
