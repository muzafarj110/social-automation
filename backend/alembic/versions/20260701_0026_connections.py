"""connections — whatsapp_connections and telegram_connections tables

Revision ID: 0026_connections
Revises: 0025_proactive_items
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_connections"
down_revision: Union[str, None] = "0025_proactive_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("phone_number_id", sa.String(), nullable=False),
        sa.Column("access_token_enc", sa.String(), nullable=False),
        sa.Column("display_phone", sa.String(), nullable=True),
        sa.Column("verified_name", sa.String(), nullable=True),
        sa.Column("to_number", sa.String(), nullable=True),
        sa.Column("auto_post", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "telegram_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("bot_token_enc", sa.String(), nullable=False),
        sa.Column("bot_username", sa.String(), nullable=True),
        sa.Column("channel_id", sa.String(), nullable=True),
        sa.Column("auto_post", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("telegram_connections")
    op.drop_table("whatsapp_connections")
