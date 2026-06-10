"""initial schema: users, linkedin_accounts, posts

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-10

Hand-authored to match app/models/*.py exactly. After this baseline, generate
future revisions with:  alembic revision --autogenerate -m "message"
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("hub_api_key_enc", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "linkedin_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("zernio_account_id", sa.String(length=128), nullable=False),
        sa.Column("account_type", sa.String(length=20), nullable=False, server_default="personal"),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="connected"),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_linkedin_accounts_user_id", "linkedin_accounts", ["user_id"])
    op.create_index("ix_linkedin_accounts_zernio_account_id", "linkedin_accounts", ["zernio_account_id"])

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column("media", sa.JSON(), nullable=True),
        sa.Column("first_comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("zernio_post_id", sa.String(length=128), nullable=True),
        sa.Column("platform_post_url", sa.String(length=512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["linkedin_accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_posts_user_id", "posts", ["user_id"])
    op.create_index("ix_posts_account_id", "posts", ["account_id"])
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_zernio_post_id", "posts", ["zernio_post_id"])


def downgrade() -> None:
    op.drop_index("ix_posts_zernio_post_id", table_name="posts")
    op.drop_index("ix_posts_status", table_name="posts")
    op.drop_index("ix_posts_account_id", table_name="posts")
    op.drop_index("ix_posts_user_id", table_name="posts")
    op.drop_table("posts")

    op.drop_index("ix_linkedin_accounts_zernio_account_id", table_name="linkedin_accounts")
    op.drop_index("ix_linkedin_accounts_user_id", table_name="linkedin_accounts")
    op.drop_table("linkedin_accounts")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
