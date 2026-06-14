"""users.zernio_profile_id — white-label per-customer Zernio profile

Revision ID: 0016_user_zernio_profile
Revises: 0015_leads
Create Date: 2026-06-13
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_user_zernio_profile"
down_revision: Union[str, None] = "0015_leads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("zernio_profile_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "zernio_profile_id")
