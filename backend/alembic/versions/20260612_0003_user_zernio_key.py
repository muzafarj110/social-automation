"""add users.zernio_api_key_enc (per-user Zernio key)

Revision ID: 0003_user_zernio_key
Revises: 0002_approvals
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_user_zernio_key"
down_revision: Union[str, None] = "0002_approvals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("zernio_api_key_enc", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "zernio_api_key_enc")
