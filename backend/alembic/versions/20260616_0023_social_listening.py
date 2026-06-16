"""social_listening — listening agent topics table

Revision ID: 0023_social_listening
Revises: 0022_competitors
Create Date: 2026-06-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0023_social_listening"
down_revision: Union[str, None] = "0022_competitors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listening_topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "platform",
            sa.String(length=50),
            server_default="linkedin",
            nullable=False,
        ),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_listening_topics_user_id", "listening_topics", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_listening_topics_user_id", table_name="listening_topics")
    op.drop_table("listening_topics")
