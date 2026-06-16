"""agency multi-client: clients table + scoping columns

Revision ID: 0021_clients
Revises: 0020_team_runs
Create Date: 2026-06-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0021_clients"
down_revision: Union[str, None] = "0020_team_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agency_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("brand_name", sa.String(length=200), nullable=True),
        sa.Column("industry", sa.String(length=200), nullable=True),
        sa.Column("audience", sa.String(length=255), nullable=True),
        sa.Column("voice", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("positioning", sa.Text(), nullable=True),
        sa.Column("docs", sa.JSON(), nullable=True),
        sa.Column("zernio_profile_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_clients_agency_user_id", "clients", ["agency_user_id"])

    op.add_column("users", sa.Column("active_client_id", sa.Integer(), nullable=True))
    op.add_column("posts", sa.Column("client_id", sa.Integer(), nullable=True))
    op.add_column("team_runs", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_index("ix_posts_client_id", "posts", ["client_id"])
    op.create_index("ix_team_runs_client_id", "team_runs", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_team_runs_client_id", table_name="team_runs")
    op.drop_index("ix_posts_client_id", table_name="posts")
    op.drop_column("team_runs", "client_id")
    op.drop_column("posts", "client_id")
    op.drop_column("users", "active_client_id")
    op.drop_index("ix_clients_agency_user_id", table_name="clients")
    op.drop_table("clients")
