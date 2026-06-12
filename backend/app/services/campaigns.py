"""
Campaign orchestrator — the autopilot engine.

Given a Campaign, it figures out what topics to post, generates each post via the
Hub (existing models only), assigns time slots from the campaign's cadence, and
either schedules them through Zernio (auto mode) or leaves them as drafts for the
user to approve (approve mode). Pure orchestration — no new AI.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.clients.hub_client import HubClient, HubError
from app.core.config import settings
from app.core.user_keys import resolve_hub_key, resolve_zernio_key
from app.models import campaign as cstate
from app.models import post as post_status
from app.models.account import LinkedInAccount
from app.models.campaign import Campaign
from app.models.post import Post
from app.models.user import User
from app.services import publisher


class CampaignError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def next_slots(campaign: Campaign, n: int, after: datetime | None = None) -> list[datetime]:
    """Compute the next `n` posting times (UTC, aware) from the cadence config."""
    if n <= 0:
        return []
    tz = _tz(campaign.timezone)
    now_local = (after or datetime.now(timezone.utc)).astimezone(tz)
    try:
        hh, mm = (int(x) for x in (campaign.time_of_day or "09:00").split(":"))
    except Exception:
        hh, mm = 9, 0
    allowed = set(campaign.days) if campaign.days else None  # None = any day
    slots: list[datetime] = []
    day = now_local.date()
    for _ in range(120):  # lookahead cap
        if len(slots) >= n:
            break
        if allowed is None or day.weekday() in allowed:
            slot = datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
            if slot > now_local + timedelta(minutes=2):
                slots.append(slot.astimezone(timezone.utc))
        day = day + timedelta(days=1)
    return slots


def _extract_topics(data: dict[str, Any], n: int) -> list[str]:
    """Pull a list of topic strings out of a Hub calendar/plan response."""
    for key in ("calendar", "posts", "ideas", "schedule", "plan", "items", "topics", "days"):
        v = data.get(key)
        if isinstance(v, list) and v:
            out: list[str] = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
                elif isinstance(item, dict):
                    for k in ("topic", "title", "theme", "hook", "idea", "subject", "headline"):
                        if isinstance(item.get(k), str) and item[k].strip():
                            out.append(item[k].strip())
                            break
                if len(out) >= n:
                    break
            if out:
                return out
    return []


async def _plan_topics(campaign: Campaign, n: int, hub: HubClient) -> list[str]:
    """Goal mode: ask the Hub calendar endpoint for topic ideas (best-effort)."""
    try:
        data = await hub.call("calendar", {
            "niche": campaign.niche or campaign.name,
            "audience": campaign.audience or "professionals",
            "goal": campaign.goal or "grow following and generate leads",
            "posting_frequency": campaign.frequency_per_week,
        })
    except Exception:
        return []
    return _extract_topics(data, n)


async def resolve_topics(campaign: Campaign, n: int, hub: HubClient) -> list[str]:
    """Return exactly `n` topic strings for this run."""
    if campaign.topic_source == cstate.GOAL:
        planned = await _plan_topics(campaign, n, hub)
        if planned:
            return [planned[i % len(planned)] for i in range(n)]

    base = [t for t in (campaign.topics or []) if t and t.strip()]
    if not base:
        seed = campaign.goal or campaign.niche or campaign.name
        base = [seed]
    return [base[i % len(base)] for i in range(n)]


def _compute_next_run(campaign: Campaign) -> datetime:
    """Weekly top-up by default."""
    return datetime.now(timezone.utc) + timedelta(days=7)


async def run_campaign(campaign: Campaign, db, *, count: int | None = None) -> list[Post]:
    """Generate a batch for the campaign. Commits and returns the created posts."""
    user = await db.get(User, campaign.user_id)
    account = await db.get(LinkedInAccount, campaign.account_id)
    if user is None or account is None:
        raise CampaignError("Campaign user or account missing.", 404)

    hub_key = resolve_hub_key(user)
    if not hub_key:
        raise CampaignError("No Hub API key on file — set one in the app first.", 400)

    zkey = resolve_zernio_key(user)
    if campaign.mode == cstate.AUTO and not zkey:
        raise CampaignError("Auto mode needs your Zernio key set first.", 400)

    n = count or campaign.frequency_per_week or 3
    created: list[Post] = []

    async with HubClient(settings.hub_base_url, hub_key) as hub:
        topics = await resolve_topics(campaign, n, hub)
        slots = next_slots(campaign, len(topics))

        for topic, slot in zip(topics, slots):
            try:
                data = await hub.generate_text_post(
                    topic=topic,
                    post_type=campaign.post_type,
                    audience=campaign.audience or "professionals",
                    tone=campaign.tone,
                )
            except HubError:
                continue  # skip this slot, keep the batch going

            post = Post(
                user_id=user.id,
                account_id=account.id,
                body=data.get("full_post") or data.get("hook") or topic,
                hashtags=data.get("hashtags"),
                source="generated",
                campaign_id=campaign.id,
                status=post_status.DRAFT,
                scheduled_for=slot,
                timezone=campaign.timezone,
            )
            db.add(post)
            await db.flush()  # assign id (used in the idempotency key)

            if campaign.mode == cstate.AUTO:
                try:
                    await publisher.schedule(
                        post, account.zernio_account_id, slot,
                        campaign.timezone, zernio_key=zkey,
                    )
                except publisher.PublishError as e:
                    post.status = post_status.FAILED
                    post.error = e.message
            created.append(post)

    campaign.last_run_at = datetime.now(timezone.utc)
    campaign.next_run_at = _compute_next_run(campaign)
    campaign.last_error = None if created else "No posts were generated this run."
    await db.commit()
    for p in created:
        await db.refresh(p)
    return created
