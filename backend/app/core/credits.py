"""
Usage-based billing — credit metering for AI actions.

AI actions cost credits; users buy more via Stripe (see app/api/billing.py).
Admins are never charged. Costs are deliberately simple — one credit per
produced post / generation — and easy to tune here.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import is_admin
from app.models.user import User

# Cost table (credits). Keep small and legible; tune as pricing evolves.
COST_GENERATE = 1          # one Quick-post generation
COST_CAMPAIGN_POST = 1     # each post a campaign produces

_OUT_OF_CREDITS = (
    "You're out of credits. Top up under Billing to keep creating."
)


def has_credits(user: User, n: int = 1) -> bool:
    return is_admin(user) or user.credits >= n


async def charge(db: AsyncSession, user: User, n: int = 1) -> None:
    """Deduct credits for an HTTP action, or raise 402 if the user can't afford it."""
    if is_admin(user):
        return
    if user.credits < n:
        raise HTTPException(402, _OUT_OF_CREDITS)
    user.credits -= n
    await db.commit()
