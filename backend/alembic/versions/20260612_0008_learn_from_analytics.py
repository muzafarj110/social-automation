"""campaigns.learn_from_analytics (closed analytics loop)

Revision ID: 0008_learn_from_analytics
Revises: 0007_infographic
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_learn_from_analytics"
down_revision: Union[str, None] = "0007_infographic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("learn_from_analytics", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "learn_from_analytics")
