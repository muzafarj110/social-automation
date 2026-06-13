"""Lead model — a simple CRM record for lead-gen / outreach."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass

# status pipeline
NEW = "new"
CONTACTED = "contacted"
QUALIFIED = "qualified"
WON = "won"
LOST = "lost"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    handle: Mapped[str | None] = mapped_column(String(200), nullable=True)   # email / @handle / URL
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)  # where they came from
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)   # e.g. "comment", "import"
    status: Mapped[str] = mapped_column(String(20), default=NEW, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft: Mapped[str | None] = mapped_column(Text, nullable=True)           # AI-drafted outreach

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
