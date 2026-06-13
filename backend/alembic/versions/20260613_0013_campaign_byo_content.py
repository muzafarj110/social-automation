"""campaigns.byo_content — user-supplied content for non-LinkedIn platforms

Revision ID: 0013_campaign_byo_content
Revises: 0012_automation_paused
Create Date: 2026-06-13
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_campaign_byo_content"
down_revision: Union[str, None] = "0012_automation_paused"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("byo_content", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "byo_content")
