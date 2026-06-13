"""
BrandProfile — the customer's marketing 'brain': who they are, their voice,
audience, positioning, and saved strategy artifacts. One per user. Generated
via Hub models, stored here, and used to keep all content on-brand.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    brand_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice: Mapped[str | None] = mapped_column(Text, nullable=True)        # tone/voice
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    positioning: Mapped[str | None] = mapped_column(Text, nullable=True)  # UVP

    # saved generated artifacts (persona, uvp, competitor, content_strategy, ...)
    docs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
