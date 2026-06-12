"""campaigns: ai_timing + post_types

Revision ID: 0005_campaign_ai_timing
Revises: 0004_campaigns
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_campaign_ai_timing"
down_revision: Union[str, None] = "0004_campaigns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("post_types", sa.JSON(), nullable=True))
    op.add_column(
        "campaigns",
        sa.Column("ai_timing", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "ai_timing")
    op.drop_column("campaigns", "post_types")
