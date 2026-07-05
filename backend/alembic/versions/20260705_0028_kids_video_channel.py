"""kids video channel — add kids_educational content type support

Revision ID: 0028_kids_video_channel
Revises: 0027_video_agent
Create Date: 2026-07-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_kids_video_channel"
down_revision: Union[str, None] = "0027_video_agent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend video_channels table with kids-specific fields
    op.add_column("video_channels", sa.Column("content_type", sa.String(50), server_default="faceless", nullable=False))
    op.add_column("video_channels", sa.Column("target_age_min", sa.Integer(), server_default=0, nullable=False))
    op.add_column("video_channels", sa.Column("target_age_max", sa.Integer(), server_default=5, nullable=False))
    op.add_column("video_channels", sa.Column("primary_theme", sa.String(50), nullable=True))
    op.add_column("video_channels", sa.Column("character_style", sa.String(255), nullable=True))
    op.add_column("video_channels", sa.Column("color_palette", sa.String(512), nullable=True))
    op.add_column("video_channels", sa.Column("music_preference", sa.String(50), nullable=True))

    # Extend generated_videos table with kids-specific progress tracking
    op.add_column("generated_videos", sa.Column("content_type", sa.String(50), server_default="faceless", nullable=False))
    op.add_column("generated_videos", sa.Column("generation_status", sa.String(50), nullable=True))
    op.add_column("generated_videos", sa.Column("generation_metadata", sa.JSON(), nullable=True))

    # Create kids_video_asset table for character/background library
    op.create_table(
        "kids_video_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("video_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(2048), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_kids_video_assets_user_id", "kids_video_assets", ["user_id"])
    op.create_index("ix_kids_video_assets_channel_id", "kids_video_assets", ["channel_id"])
    op.create_index("ix_kids_video_assets_asset_type", "kids_video_assets", ["asset_type"])


def downgrade() -> None:
    op.drop_table("kids_video_assets")

    op.drop_column("generated_videos", "generation_metadata")
    op.drop_column("generated_videos", "generation_status")
    op.drop_column("generated_videos", "content_type")

    op.drop_column("video_channels", "music_preference")
    op.drop_column("video_channels", "color_palette")
    op.drop_column("video_channels", "character_style")
    op.drop_column("video_channels", "primary_theme")
    op.drop_column("video_channels", "target_age_max")
    op.drop_column("video_channels", "target_age_min")
    op.drop_column("video_channels", "content_type")
