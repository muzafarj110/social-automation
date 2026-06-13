"""users.profile_type + entitlements_override (onboarding + plan gating)

Revision ID: 0010_user_profile_entitlements
Revises: 0009_brand_profiles
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_user_profile_entitlements"
down_revision: Union[str, None] = "0009_brand_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_type", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("entitlements_override", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "entitlements_override")
    op.drop_column("users", "profile_type")
