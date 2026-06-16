"""seo_projects — SEO + GEO agent table

Revision ID: 0024_seo_projects
Revises: 0023_social_listening
Create Date: 2026-06-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0024_seo_projects"
down_revision: Union[str, None] = "0023_social_listening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seo_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("target_keywords", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_seo_projects_user_id", "seo_projects", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_seo_projects_user_id", table_name="seo_projects")
    op.drop_table("seo_projects")
