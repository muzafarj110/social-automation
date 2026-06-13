"""brand_profiles (strategy brain)

Revision ID: 0009_brand_profiles
Revises: 0008_learn_from_analytics
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_brand_profiles"
down_revision: Union[str, None] = "0008_learn_from_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("brand_name", sa.String(length=200), nullable=True),
        sa.Column("industry", sa.String(length=200), nullable=True),
        sa.Column("audience", sa.String(length=255), nullable=True),
        sa.Column("voice", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("positioning", sa.Text(), nullable=True),
        sa.Column("docs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_brand_profiles_user_id", "brand_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_brand_profiles_user_id", table_name="brand_profiles")
    op.drop_table("brand_profiles")
