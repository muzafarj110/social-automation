"""users subscription fields — Stripe recurring plans + monthly credit allowance

Revision ID: 0018_user_subscriptions
Revises: 0017_password_reset_tokens
Create Date: 2026-06-15
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_user_subscriptions"
down_revision: Union[str, None] = "0017_password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("subscription_tier", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("subscription_renews_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "subscription_renews_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "subscription_tier")
    op.drop_column("users", "stripe_customer_id")
