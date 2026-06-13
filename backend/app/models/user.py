"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    plan: Mapped[str] = mapped_column(String(20), default="free")       # free | pro | business
    status: Mapped[str] = mapped_column(String(20), default="active")   # active | suspended
    # set during onboarding: individual | influencer | startup | company
    profile_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # admin per-user feature overrides (merged over plan defaults), e.g. {"autopilot": true}
    entitlements_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # global kill-switch: when true, no campaign auto-publishes — everything
    # becomes a draft the user must approve. Their safety net.
    automation_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # usage-based billing: AI actions spend credits; bought via Stripe.
    credits: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Per-user AI Models Hub key, encrypted at rest (Fernet). May be null until set.
    hub_api_key_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Per-user Zernio key, encrypted at rest. Scopes which LinkedIn accounts the
    # user can see/post to — the basis of multi-tenant isolation.
    zernio_api_key_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    accounts: Mapped[list["LinkedInAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


from app.models.account import LinkedInAccount  # noqa: E402
