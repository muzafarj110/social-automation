"""users.credits — usage-based billing balance

Revision ID: 0014_user_credits
Revises: 0013_campaign_byo_content
Create Date: 2026-06-13
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_user_credits"
down_revision: Union[str, None] = "0013_campaign_byo_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("credits", sa.Integer(), nullable=False, server_default="50"),
    )


def downgrade() -> None:
    op.drop_column("users", "credits")
