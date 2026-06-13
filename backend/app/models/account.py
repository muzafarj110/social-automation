"""Linked social account (via Zernio) — any supported platform.

The table/class keep their original `linkedin_accounts` / `LinkedInAccount`
names for migration continuity, but a row now represents an account on ANY
platform (see the `platform` column)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Which social platform this account is on (twitter, instagram, linkedin, …).
    # Defaults to linkedin for rows created before multi-platform support.
    platform: Mapped[str] = mapped_column(String(32), default="linkedin", index=True)
    # The account id Zernio assigns to the connected account.
    zernio_account_id: Mapped[str] = mapped_column(String(128), index=True)
    account_type: Mapped[str] = mapped_column(String(20), default="personal")  # personal | organization
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="connected")  # connected | disconnected

    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="accounts")
