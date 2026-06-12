"""campaigns table + posts.campaign_id (autopilot)

Revision ID: 0004_campaigns
Revises: 0003_user_zernio_key
Create Date: 2026-06-12

Matches app/models/campaign.py and the new Post.campaign_id column.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_campaigns"
down_revision: Union[str, None] = "0003_user_zernio_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="approve"),
        sa.Column("topic_source", sa.String(length=20), nullable=False, server_default="topics"),
        sa.Column("topics", sa.JSON(), nullable=True),
        sa.Column("niche", sa.String(length=255), nullable=True),
        sa.Column("goal", sa.String(length=255), nullable=True),
        sa.Column("audience", sa.String(length=255), nullable=True),
        sa.Column("tone", sa.String(length=120), nullable=False, server_default="professional but human"),
        sa.Column("post_type", sa.String(length=120), nullable=False, server_default="Personal Story + Lesson"),
        sa.Column("frequency_per_week", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("days", sa.JSON(), nullable=True),
        sa.Column("time_of_day", sa.String(length=5), nullable=False, server_default="09:00"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["linkedin_accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_campaigns_user_id", "campaigns", ["user_id"])
    op.create_index("ix_campaigns_account_id", "campaigns", ["account_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("ix_campaigns_next_run_at", "campaigns", ["next_run_at"])

    # batch mode so this also works on SQLite (no ALTER ADD CONSTRAINT there)
    with op.batch_alter_table("posts") as batch:
        batch.add_column(sa.Column("campaign_id", sa.Integer(), nullable=True))
        batch.create_index("ix_posts_campaign_id", ["campaign_id"])
        batch.create_foreign_key(
            "fk_posts_campaign_id", "campaigns",
            ["campaign_id"], ["id"], ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("posts") as batch:
        batch.drop_constraint("fk_posts_campaign_id", type_="foreignkey")
        batch.drop_index("ix_posts_campaign_id")
        batch.drop_column("campaign_id")

    op.drop_index("ix_campaigns_next_run_at", table_name="campaigns")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_account_id", table_name="campaigns")
    op.drop_index("ix_campaigns_user_id", table_name="campaigns")
    op.drop_table("campaigns")
