"""
Campaign orchestrator — the autopilot engine.

Given a Campaign, it figures out what topics to post, generates each post via the
Hub (existing models only), assigns time slots from the campaign's cadence, and
either schedules them through Zernio (auto mode) or leaves them as drafts for the
user to approve (approve mode). Pure orchestration — no new AI.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.clients.hub_client import HubClient, HubError
from app.clients.zernio_client import ZernioClient
from app.core import platforms as plat
from app.core.config import settings
from app.core.user_keys import resolve_hub_key, resolve_zernio_key
from app.models import campaign as cstate
from app.models import post as post_status
from app.models.account import LinkedInAccount
from app.models.brand import BrandProfile
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


def next_slots(
    campaign: Campaign, n: int, after: datetime | None = None,
    *, days: list[int] | None = None, time_of_day: str | None = None,
) -> list[datetime]:
    """Compute the next `n` posting times (UTC, aware) from the cadence config.

    `days`/`time_of_day` override the campaign's values (used by AI timing).
    """
    if n <= 0:
        return []
    tz = _tz(campaign.timezone)
    now_local = (after or datetime.now(timezone.utc)).astimezone(tz)
    tod = time_of_day or campaign.time_of_day or "09:00"
    try:
        hh, mm = (int(x) for x in tod.split(":"))
    except Exception:
        hh, mm = 9, 0
    use_days = days if days is not None else campaign.days
    allowed = set(use_days) if use_days else None  # None = any day
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


# --- AI-suggested timing ----------------------------------------------------
_WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2,
    "wed": 2, "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4,
    "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.I)
# LinkedIn best-practice fallback windows (Tue/Wed/Thu mornings, then Mon/Fri).
_BEST_DAYS = [1, 2, 3, 0, 4]
_BEST_TIME = "08:00"


def _all_strings(obj: Any) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        out: list[str] = []
        for v in obj.values():
            out.extend(_all_strings(v))
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            out.extend(_all_strings(v))
        return out
    return []


def _norm_time(m: re.Match) -> str | None:
    h = int(m.group(1))
    mm = int(m.group(2) or 0)
    ap = (m.group(3) or "").lower()
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if 0 <= h <= 23 and 0 <= mm <= 59:
        return f"{h:02d}:{mm:02d}"
    return None


async def ai_timing(campaign: Campaign, hub: HubClient) -> tuple[list[int], str]:
    """Ask the Hub's engagement-strategy for posting days/times; fall back to
    LinkedIn best-practice windows. Returns (days, "HH:MM")."""
    days: list[int] | None = None
    time_str: str | None = None
    try:
        data = await hub.call("engagement_strategy", {
            "niche": campaign.niche or campaign.audience or campaign.name,
            "current_posting_frequency": f"{campaign.frequency_per_week}x per week",
            "follower_goal": 5000,
        })
        blob = " ".join(_all_strings(data)).lower()
        found = sorted({
            d for name, d in _WEEKDAYS.items()
            if re.search(r"\b" + re.escape(name) + r"\b", blob)
        })
        if found:
            days = found
        m = _TIME_RE.search(blob)
        if m:
            time_str = _norm_time(m)
    except Exception:
        pass
    if not days:
        count = max(1, min(campaign.frequency_per_week or 3, len(_BEST_DAYS)))
        days = _BEST_DAYS[:count]
    return days, (time_str or _BEST_TIME)


_OPTIMIZED_KEYS = ("optimized_content", "optimized", "improved_content", "improved",
                   "rewritten", "rewrite", "content", "full_post", "result")


async def qa_and_polish(hub: HubClient, content: str, tone: str) -> str:
    """Score content; if below par (<75), rewrite it via content-optimizer.

    Best-effort and non-fatal — always returns usable content. This is what
    makes the autopilot vet its own output before scheduling.
    """
    try:
        sd = await hub.call("score_checker", {"content": content, "platform": "linkedin"})
        score = sd.get("overall_score")
        if not isinstance(score, (int, float)):
            score = sd.get("score") if isinstance(sd.get("score"), (int, float)) else None
    except Exception:
        return content
    if not isinstance(score, (int, float)) or score >= 75:
        return content
    try:
        opt = await hub.call("content_optimizer",
                             {"content": content, "goal": "engagement", "tone": tone})
    except Exception:
        return content
    for k in _OPTIMIZED_KEYS:
        v = opt.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return content


async def performance_signal(user: User) -> list[str]:
    """The themes of the user's best-performing posts (Zernio analytics).

    Best-effort: returns content snippets of the top posts that actually got
    engagement, so the autopilot can double down on what works. Empty when
    there's no Zernio key or no engagement data yet.
    """
    key = resolve_zernio_key(user)
    if not key:
        return []
    try:
        async with ZernioClient(settings.zernio_base_url, key) as z:
            data = await z.get_analytics(platform="linkedin")
    except Exception:
        return []
    scored: list[tuple[int, str]] = []
    for p in (data.get("posts") or []):
        a = p.get("analytics") or {}
        eng = (int(a.get("impressions") or 0)
               + 5 * int(a.get("likes") or 0)
               + 10 * int(a.get("comments") or 0))
        content = (p.get("content") or "").strip()
        if content and eng > 0:
            scored.append((eng, content))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [c for _, c in scored[:3]]


async def tailor_for_platform(
    hub: HubClient, content: str, platform: str, tone: str
) -> str:
    """Rewrite `content` to fit one platform's norms via the Hub content-optimizer.

    Uses an EXISTING Hub model (no new AI in the app). Best-effort: on any
    failure we return the original content (the publisher still trims it to the
    platform's character limit). LinkedIn is the base voice, so we skip the
    extra call for it.
    """
    if platform == "linkedin":
        return content
    goal = (f"Rewrite this post natively for {plat.label(platform)} "
            f"(max {plat.char_limit(platform)} characters, match the platform's "
            f"style and conventions). Keep the core message.")
    try:
        opt = await hub.call("content_optimizer",
                             {"content": content, "goal": goal, "tone": tone})
    except Exception:
        return content
    for k in _OPTIMIZED_KEYS:
        v = opt.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return content


async def _platform_accounts(
    campaign: Campaign, primary: LinkedInAccount, db
) -> dict[str, LinkedInAccount]:
    """Map each target platform to one of the user's connected accounts.

    Targets = campaign.platforms (validated) or just the primary account's
    platform. The primary account is always used for its own platform; for the
    others we pick the user's first connected account on that platform.
    Platforms with no connected account are simply skipped.
    """
    targets = [plat.normalize(p) for p in (campaign.platforms or [])] or [primary.platform]
    mapping: dict[str, LinkedInAccount] = {primary.platform: primary}
    missing = [p for p in targets if p not in mapping]
    if missing:
        rows = await db.scalars(
            select(LinkedInAccount).where(
                LinkedInAccount.user_id == campaign.user_id,
                LinkedInAccount.platform.in_(missing),
            )
        )
        for acc in rows:
            mapping.setdefault(acc.platform, acc)
    # Keep only the requested targets, in request order.
    return {p: mapping[p] for p in targets if p in mapping}


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

    # Which platforms to post to, mapped to a connected account each.
    pacc = await _platform_accounts(campaign, account, db)
    if not pacc:
        raise CampaignError("No connected account for the campaign's platforms.", 400)

    n = count or campaign.frequency_per_week or 3
    created: list[Post] = []

    # angles to rotate through (content variety); fall back to the single type
    angles = [a for a in (campaign.post_types or []) if a and a.strip()] or [campaign.post_type]

    # strategy brain: keep every post on-brand (voice + audience)
    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == user.id))
    brand_voice = (brand.voice or "").strip() if brand else ""
    brand_audience = (brand.audience or "").strip() if brand else ""

    # closed loop: double down on what's already performing
    winners = await performance_signal(user) if campaign.learn_from_analytics else []

    async with HubClient(settings.hub_base_url, hub_key) as hub:
        topics = await resolve_topics(campaign, n, hub)
        if winners:
            # every other slot riffs on a proven, high-performing theme
            for i in range(0, len(topics), 2):
                w = winners[(i // 2) % len(winners)]
                topics[i] = f"A fresh angle on this proven, high-performing theme: {w[:200]}"
        if campaign.ai_timing:
            ai_days, ai_time = await ai_timing(campaign, hub)
            slots = next_slots(campaign, len(topics), days=ai_days, time_of_day=ai_time)
        else:
            slots = next_slots(campaign, len(topics))

        for i, (topic, slot) in enumerate(zip(topics, slots)):
            try:
                data = await hub.generate_text_post(
                    topic=topic,
                    post_type=angles[i % len(angles)],
                    audience=campaign.audience or brand_audience or "professionals",
                    tone=brand_voice or campaign.tone,
                )
            except HubError:
                continue  # skip this slot, keep the batch going

            body_text = data.get("full_post") or data.get("hook") or topic
            if campaign.auto_improve:
                body_text = await qa_and_polish(hub, body_text, campaign.tone)

            # One infographic per idea, shared across platform variants.
            ig_html = None
            if campaign.with_infographic:
                try:
                    ig = await hub.call("infographic",
                                        {"topic": topic, "content_points": body_text[:1000]})
                    ig_html = ig.get("html")
                except Exception:
                    ig_html = None

            hashtags = data.get("hashtags")

            # Fan the idea out to every target platform, tailored to each.
            for platform, acc in pacc.items():
                variant = await tailor_for_platform(hub, body_text, platform, campaign.tone)
                post = Post(
                    user_id=user.id,
                    account_id=acc.id,
                    platform=platform,
                    body=variant,
                    hashtags=hashtags,
                    source="generated",
                    campaign_id=campaign.id,
                    status=post_status.DRAFT,
                    scheduled_for=slot,
                    timezone=campaign.timezone,
                    infographic_html=ig_html,
                )
                db.add(post)
                await db.flush()  # assign id (used in the idempotency key)

                if publisher.needs_media(post, platform):
                    # IG/TikTok/etc. reject text-only — keep as a draft for the
                    # user to add an image/video, even in auto mode.
                    post.error = (f"{plat.label(platform)} needs an image or video — "
                                  f"left as a draft so you can add media.")
                elif campaign.mode == cstate.AUTO:
                    try:
                        await publisher.schedule(
                            post, acc.zernio_account_id, slot,
                            campaign.timezone, platform=platform, zernio_key=zkey,
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
