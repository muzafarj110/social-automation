"""campaigns.auto_improve (QA + auto-polish generated posts)

Revision ID: 0006_campaign_auto_improve
Revises: 0005_campaign_ai_timing
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_campaign_auto_improve"
down_revision: Union[str, None] = "0005_campaign_ai_timing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("auto_improve", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "auto_improve")
