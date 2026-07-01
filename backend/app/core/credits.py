"""
Usage-based billing — credit metering for AI actions.

Three kinds of access:
  - Admin            → unlimited.
  - Subscribed       → spends from a monthly credit balance (set on renewal).
  - Free trial       → a daily allowance (FREE_DAILY_LIMIT) for FREE_TRIAL_DAYS,
                       then must subscribe.

Charges happen only on a successful AI action; failed ones never deduct.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.config import settings
from app.core.entitlements import is_admin
from app.models.user import User

# ── Credit cost table ─────────────────────────────────────────────────────────
# Tier 1 — text generation (one Hub call, fast, cheap)
COST_GENERATE = 1        # drafts, analysis, outreach, listening scan, autopilot
COST_CAMPAIGN_POST = 1

# Tier 2 — long-form / multi-call (2+ Hub calls or large outputs)
COST_LONG_FORM = 2       # SEO+GEO, articles, carousels, newsletters, sequences

# Tier 3 — image generation (image AI model, slow, ~$0.04-0.08/image)
COST_IMAGE = 5           # social graphics, infographics, ad creatives

# Tier 4 — video generation (video AI, very slow, ~$0.50-5.00/clip)
COST_VIDEO = 15          # short clips, reels, talking-head videos
# ──────────────────────────────────────────────────────────────────────────────

_OUT_OF_CREDITS = "You're out of credits. Top up under Billing to keep creating."
_DAILY_LIMIT = "You've used your free credits for today. Come back tomorrow, or subscribe for more."
_TRIAL_OVER = "Your free trial has ended. Subscribe under Billing to keep creating."


def _today() -> str:
    return date.today().isoformat()


def is_subscribed(user: User) -> bool:
    return bool(user.subscription_tier) and user.subscription_status in ("active", "trialing")


def trial_expired(user: User) -> bool:
    # A null end date means the trial hasn't started yet — treat as active.
    if user.trial_ends_at is None:
        return False
    end = user.trial_ends_at
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > end


def free_remaining(user: User) -> int:
    used = user.free_used_today if user.free_quota_date == _today() else 0
    return max(0, settings.free_daily_limit - used)


def has_credits(user: User, n: int = 1) -> bool:
    if is_admin(user):
        return True
    if is_subscribed(user):
        return user.credits >= n
    if trial_expired(user):
        return False
    return free_remaining(user) >= n


async def charge(db, user: User, n: int = 1) -> None:
    """Deduct for an AI action, or raise 402 if the user can't afford it."""
    if is_admin(user):
        return
    if is_subscribed(user):
        if user.credits < n:
            raise HTTPException(402, _OUT_OF_CREDITS)
        user.credits -= n
        await db.commit()
        return
    # Free trial path — lazily start the trial window on first spend.
    if user.trial_ends_at is None:
        user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=settings.free_trial_days)
    if trial_expired(user):
        raise HTTPException(402, _TRIAL_OVER)
    if user.free_quota_date != _today():
        user.free_quota_date = _today()
        user.free_used_today = 0
    if user.free_used_today + n > settings.free_daily_limit:
        raise HTTPException(402, _DAILY_LIMIT)
    user.free_used_today += n
    await db.commit()
