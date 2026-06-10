"""
Approval model — the human-in-the-loop queue.

An approval holds an AI draft (from the Hub) for an action that LinkedIn's
official API either CAN do compliantly (company-page comment reply → executes
via Zernio) or CANNOT (personal comments, DMs, outreach, profile edits → the
human performs the final send/apply). See ARCHITECTURE.md §4.3 (the hybrid rule).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import LinkedInAccount
    from app.models.user import User

# kind values
COMMENT = "comment"
DM = "dm"
OUTREACH = "outreach"
PROFILE = "profile"
KINDS = {COMMENT, DM, OUTREACH, PROFILE}

# status values
PENDING = "pending"      # drafted, awaiting human
APPROVED = "approved"    # approved; ready for the human to send/apply (manual)
SENT = "sent"            # executed compliantly via Zernio
REJECTED = "rejected"    # discarded

# executed_via values
ZERNIO = "zernio"
MANUAL = "manual"


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Nullable: DM/profile drafts aren't always tied to one linked account.
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )

    kind: Mapped[str] = mapped_column(String(20), index=True)  # comment|dm|outreach|profile

    # Full Hub draft response, kept for reference / regeneration.
    ai_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # The editable text the human reviews and ultimately sends/applies.
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Targeting info: post_url, comment_id, recipient, organization_urn, etc.
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=PENDING, index=True)
    executed_via: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship()
    account: Mapped["LinkedInAccount"] = relationship()
