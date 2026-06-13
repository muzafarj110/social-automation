"""
Campaign model — an autopilot config that generates and schedules posts on a
cadence. Pure orchestration over existing Hub endpoints; no new AI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import LinkedInAccount
    from app.models.user import User

# mode (hands-off level)
AUTO = "auto"          # generate -> schedule -> Zernio publishes
APPROVE = "approve"    # generate -> drafts for the user to review/approve

# topic_source
TOPICS = "topics"      # user-supplied list of topics, rotated
GOAL = "goal"          # Hub plans topics from niche/goal (linkedin-calendar)

# status
ACTIVE = "active"
PAUSED = "paused"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(20), default=APPROVE)          # auto | approve
    topic_source: Mapped[str] = mapped_column(String(20), default=TOPICS)   # topics | goal

    # topic_source = topics
    topics: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # topic_source = goal (Hub planner inputs)
    niche: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # generation style
    audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tone: Mapped[str] = mapped_column(String(120), default="professional but human")
    post_type: Mapped[str] = mapped_column(String(120), default="Personal Story + Lesson")
    # content-angle rotation: list of post_types to cycle through (falls back to post_type)
    post_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # cadence
    frequency_per_week: Mapped[int] = mapped_column(Integer, default=3)
    days: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)  # 0=Mon..6=Sun
    time_of_day: Mapped[str] = mapped_column(String(5), default="09:00")  # "HH:MM"
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    # when true, the Hub's engagement-strategy suggests the posting days/times
    ai_timing: Mapped[bool] = mapped_column(Boolean, default=False)
    # when true, each generated post is QA-scored and auto-polished if below par
    auto_improve: Mapped[bool] = mapped_column(Boolean, default=True)
    # when true, generate an infographic (HTML) alongside each post
    with_infographic: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(String(20), default=ACTIVE, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
    account: Mapped["LinkedInAccount"] = relationship()
