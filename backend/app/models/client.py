"""
Client — an agency's managed customer (multi-tenant workspace).

One agency user can run many Clients, each isolated: its own brand, content,
posts, and (later) connected channels via its own Zernio profile. The agency's
"active client" scopes what they see and what the content team produces.

A Client carries its own brand fields directly (rather than a separate
BrandProfile per client) so brand is naturally isolated per workspace.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The agency account that owns/manages this client.
    agency_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))

    # This client's brand (its own strategy brain).
    brand_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    positioning: Mapped[str | None] = mapped_column(Text, nullable=True)
    docs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # This client's isolated channel container (set when channels are connected).
    zernio_profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
