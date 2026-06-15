"""content-team runs + post.team_run_id / qa_score

Revision ID: 0020_team_runs
Revises: 0019_email_verification_trial
Create Date: 2026-06-15
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_team_runs"
down_revision: Union[str, None] = "0019_email_verification_trial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "team_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("brief", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_team_runs_user_id", "team_runs", ["user_id"])
    op.create_index("ix_team_runs_status", "team_runs", ["status"])

    op.add_column("posts", sa.Column("team_run_id", sa.Integer(), nullable=True))
    op.add_column("posts", sa.Column("qa_score", sa.Integer(), nullable=True))
    op.create_index("ix_posts_team_run_id", "posts", ["team_run_id"])
    op.create_foreign_key(
        "fk_posts_team_run_id", "posts", "team_runs", ["team_run_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_posts_team_run_id", "posts", type_="foreignkey")
    op.drop_index("ix_posts_team_run_id", table_name="posts")
    op.drop_column("posts", "qa_score")
    op.drop_column("posts", "team_run_id")
    op.drop_index("ix_team_runs_status", table_name="team_runs")
    op.drop_index("ix_team_runs_user_id", table_name="team_runs")
    op.drop_table("team_runs")
