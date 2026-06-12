"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    plan: Mapped[str] = mapped_column(String(20), default="free")       # free | pro
    status: Mapped[str] = mapped_column(String(20), default="active")   # active | suspended

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
