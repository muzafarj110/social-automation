"""whatsapp agent — conversation/message storage + connection extensions

Revision ID: 0029_whatsapp_agent
Revises: 0028_kids_video_channel
Create Date: 2026-07-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_whatsapp_agent"
down_revision: Union[str, None] = "0028_kids_video_channel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("whatsapp_connections", sa.Column("auto_reply_enabled", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("whatsapp_connections", sa.Column("escalation_keywords", sa.String(), nullable=True))
    op.add_column("whatsapp_connections", sa.Column("webhook_verify_token", sa.String(), nullable=True))
    op.add_column("whatsapp_connections", sa.Column("app_secret_enc", sa.String(), nullable=True))

    op.create_table(
        "whatsapp_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_phone", sa.String(32), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "customer_phone", name="uq_whatsapp_conv_user_phone"),
    )
    op.create_index("ix_whatsapp_conversations_user_id", "whatsapp_conversations", ["user_id"])
    op.create_index("ix_whatsapp_conversations_customer_phone", "whatsapp_conversations", ["customer_phone"])
    op.create_index("ix_whatsapp_conversations_status", "whatsapp_conversations", ["status"])

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender", sa.String(10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("meta_message_id", sa.String(128), nullable=True, unique=True),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("flag_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_whatsapp_messages_conversation_id", "whatsapp_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_conversations")

    op.drop_column("whatsapp_connections", "app_secret_enc")
    op.drop_column("whatsapp_connections", "webhook_verify_token")
    op.drop_column("whatsapp_connections", "escalation_keywords")
    op.drop_column("whatsapp_connections", "auto_reply_enabled")
