"""TeamRun — one cycle of the agentic content team (a batch awaiting approval)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# status values
DRAFT = "draft"          # batch generated, awaiting the user's one approval
SCHEDULED = "scheduled"  # approved → posts scheduled


class TeamRun(Base):
    __tablename__ = "team_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=DRAFT, index=True)
    # The Strategist agent's brief for this cycle (what angle, why).
    brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
