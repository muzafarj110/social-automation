"""VideoChannel — a user's configuration for the video agent (Faceless Video
Pipeline integration). One channel per user/workspace to start."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VideoChannel(Base):
    __tablename__ = "video_channels"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_video_channel_user_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(120))
    handle: Mapped[str] = mapped_column(String(120))
    niche: Mapped[str] = mapped_column(Text)
    accent_color: Mapped[str] = mapped_column(String(16), default="#7c4dff")
    music_style: Mapped[str] = mapped_column(String(20), default="calm")
    tts_voice: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claude_system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    pexels_fallback_keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    short_clips: Mapped[int] = mapped_column(Integer, default=6)
    long_clips: Mapped[int] = mapped_column(Integer, default=18)
    clip_duration: Mapped[int] = mapped_column(Integer, default=8)
    pexels_orientation: Mapped[str] = mapped_column(String(16), default="portrait")

    # "Memory-first" cache window — how long a completed video for the same
    # topic is reused before generating fresh. User-configurable.
    cache_duration_days: Mapped[int] = mapped_column(Integer, default=7)

    # Kids video content type fields
    content_type: Mapped[str] = mapped_column(String(50), default="faceless")
    target_age_min: Mapped[int] = mapped_column(Integer, default=0)
    target_age_max: Mapped[int] = mapped_column(Integer, default=5)
    primary_theme: Mapped[str | None] = mapped_column(String(50), nullable=True)
    character_style: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color_palette: Mapped[str | None] = mapped_column(String(512), nullable=True)
    music_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_pipeline_dict(self) -> dict[str, Any]:
        """Shape expected by the vendored pipeline's channels/<name>.yaml schema."""
        return {
            "name": self.name,
            "handle": self.handle,
            "niche": self.niche,
            "accent_color": self.accent_color,
            "music_style": self.music_style,
            "tts_voice": self.tts_voice or "",
            "short_clips": self.short_clips,
            "long_clips": self.long_clips,
            "clip_duration": self.clip_duration,
            "pexels_orientation": self.pexels_orientation,
            "claude_system_prompt": self.claude_system_prompt or "",
            "pexels_fallback_keywords": self.pexels_fallback_keywords or [],
        }
