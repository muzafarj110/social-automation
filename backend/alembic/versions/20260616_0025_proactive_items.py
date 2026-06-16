"""proactive_items — auto-generated live work feed items

Revision ID: 0025_proactive_items
Revises: 0024_seo_projects
Create Date: 2026-06-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0025_proactive_items"
down_revision: Union[str, None] = "0024_seo_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proactive_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_tab", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="new",
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_proactive_items_user_id", "proactive_items", ["user_id"])
    op.create_index("ix_proactive_items_generated_at", "proactive_items", ["generated_at"])


def downgrade() -> None:
    op.drop_index("ix_proactive_items_generated_at", table_name="proactive_items")
    op.drop_index("ix_proactive_items_user_id", table_name="proactive_items")
    op.drop_table("proactive_items")
