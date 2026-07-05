"""GeneratedVideo — one video-agent job: request, status, and (once complete)
the output file URLs and generated metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# status values
QUEUED = "queued"
GENERATING = "generating"
COMPLETED = "completed"
FAILED = "failed"


class GeneratedVideo(Base):
    __tablename__ = "generated_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("video_channels.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )

    topic: Mapped[str] = mapped_column(Text)
    # sha256(channel_id + normalized topic) — the cache lookup key.
    topic_cache_key: Mapped[str] = mapped_column(String(64), index=True)

    status: Mapped[str] = mapped_column(String(20), default=QUEUED, index=True)
    # coarse step label for the polling UI: "script"|"clips"|"audio"|"render"|
    # "captions"|"thumbnail" — set by the service layer as the job progresses.
    progress_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashtags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    youtube_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    youtube_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiktok_caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    video_short_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_long_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    srt_short_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    srt_long_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    short_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    long_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Kids video content type fields
    content_type: Mapped[str] = mapped_column(String(50), default="faceless")
    generation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generation_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    @property
    def has_short(self) -> bool:
        return bool(self.video_short_url)

    @property
    def has_long(self) -> bool:
        return bool(self.video_long_url)
