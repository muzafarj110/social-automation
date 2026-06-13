"""multi-platform: accounts.platform, posts.platform, campaigns.platforms

Revision ID: 0011_multi_platform
Revises: 0010_user_profile_entitlements
Create Date: 2026-06-13
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_multi_platform"
down_revision: Union[str, None] = "0010_user_profile_entitlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows are all LinkedIn — backfill with a server default, then keep
    # the default for new rows too (harmless and simplifies inserts).
    op.add_column(
        "linkedin_accounts",
        sa.Column("platform", sa.String(length=32), nullable=False, server_default="linkedin"),
    )
    op.create_index("ix_linkedin_accounts_platform", "linkedin_accounts", ["platform"])

    op.add_column(
        "posts",
        sa.Column("platform", sa.String(length=32), nullable=False, server_default="linkedin"),
    )
    op.create_index("ix_posts_platform", "posts", ["platform"])

    op.add_column("campaigns", sa.Column("platforms", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "platforms")
    op.drop_index("ix_posts_platform", table_name="posts")
    op.drop_column("posts", "platform")
    op.drop_index("ix_linkedin_accounts_platform", table_name="linkedin_accounts")
    op.drop_column("linkedin_accounts", "platform")
