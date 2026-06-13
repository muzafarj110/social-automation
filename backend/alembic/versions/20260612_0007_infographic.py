"""posts.infographic_html + campaigns.with_infographic

Revision ID: 0007_infographic
Revises: 0006_campaign_auto_improve
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_infographic"
down_revision: Union[str, None] = "0006_campaign_auto_improve"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("infographic_html", sa.Text(), nullable=True))
    op.add_column(
        "campaigns",
        sa.Column("with_infographic", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "with_infographic")
    op.drop_column("posts", "infographic_html")
