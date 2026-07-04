"""video agent — video_channels and generated_videos tables

Revision ID: 0027_video_agent
Revises: 0026_connections
Create Date: 2026-07-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_video_agent"
down_revision: Union[str, None] = "0026_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("handle", sa.String(120), nullable=False),
        sa.Column("niche", sa.Text(), nullable=False),
        sa.Column("accent_color", sa.String(16), nullable=False, server_default="#7c4dff"),
        sa.Column("music_style", sa.String(20), nullable=False, server_default="calm"),
        sa.Column("tts_voice", sa.String(64), nullable=True),
        sa.Column("claude_system_prompt", sa.Text(), nullable=True),
        sa.Column("pexels_fallback_keywords", sa.JSON(), nullable=True),
        sa.Column("short_clips", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("long_clips", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("clip_duration", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("pexels_orientation", sa.String(16), nullable=False, server_default="portrait"),
        sa.Column("cache_duration_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "client_id", name="uq_video_channel_user_client"),
    )
    op.create_index("ix_video_channels_user_id", "video_channels", ["user_id"])
    op.create_index("ix_video_channels_client_id", "video_channels", ["client_id"])

    op.create_table(
        "generated_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("video_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("topic_cache_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("progress_step", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column("youtube_title", sa.String(255), nullable=True),
        sa.Column("youtube_description", sa.Text(), nullable=True),
        sa.Column("tiktok_caption", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("video_short_url", sa.String(512), nullable=True),
        sa.Column("video_long_url", sa.String(512), nullable=True),
        sa.Column("srt_short_url", sa.String(512), nullable=True),
        sa.Column("srt_long_url", sa.String(512), nullable=True),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("short_post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("long_post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_generated_videos_user_id", "generated_videos", ["user_id"])
    op.create_index("ix_generated_videos_channel_id", "generated_videos", ["channel_id"])
    op.create_index("ix_generated_videos_client_id", "generated_videos", ["client_id"])
    op.create_index("ix_generated_videos_topic_cache_key", "generated_videos", ["topic_cache_key"])
    op.create_index("ix_generated_videos_status", "generated_videos", ["status"])
    op.create_index("ix_generated_videos_short_post_id", "generated_videos", ["short_post_id"])
    op.create_index("ix_generated_videos_long_post_id", "generated_videos", ["long_post_id"])
    # Composite index for the cache lookup: WHERE channel_id=? AND
    # topic_cache_key=? AND status='completed' AND completed_at >= cutoff.
    op.create_index(
        "ix_generated_videos_cache_lookup",
        "generated_videos",
        ["channel_id", "topic_cache_key", "completed_at"],
    )


def downgrade() -> None:
    op.drop_table("generated_videos")
    op.drop_table("video_channels")
