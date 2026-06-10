"""Post model — a LinkedIn post in draft / scheduled / published state."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import LinkedInAccount
    from app.models.user import User

# status values
DRAFT = "draft"
SCHEDULED = "scheduled"
PUBLISHED = "published"
FAILED = "failed"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), index=True
    )

    body: Mapped[str] = mapped_column(Text)
    hashtags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    media: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    first_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=DRAFT, index=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")

    # Zernio bookkeeping
    zernio_post_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    platform_post_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # how it was created: 'manual' | 'generated'
    source: Mapped[str] = mapped_column(String(20), default="manual")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
    account: Mapped["LinkedInAccount"] = relationship()
