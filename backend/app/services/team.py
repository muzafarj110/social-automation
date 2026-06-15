"""
Content Team — orchestrates the agentic cycle into a batch of draft posts.

Stages (one cycle): Strategist (brand + strategy) → Packager/Writer (per-post
drafts) → Producer (QA score). The batch lands as draft Posts tied to a TeamRun,
which the user approves once; approval schedules them across the coming week.

Resilient by design: any single Hub call failing skips that item rather than
breaking the whole batch, so a flaky model never wipes the run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.clients.hub_client import HubClient, HubError
from app.core import credits
from app.core.config import settings
from app.core.user_keys import resolve_hub_key, resolve_zernio_key
from app.models import post as post_status
from app.models import team_run as team_status
from app.models.account import LinkedInAccount
from app.models.brand import BrandProfile
from app.models.post import Post
from app.models.team_run import TeamRun
from app.models.user import User
from app.services import publisher

log = logging.getLogger("uvicorn.error")


class TeamError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _topics_from_strategy(data, count: int) -> list[str]:
    """Pull post topics/angles out of a Hub content_strategy response."""
    topics: list[str] = []
    if isinstance(data, dict):
        for key in ("content_pillars", "pillars", "topics", "ideas", "posts", "content_ideas"):
            v = data.get(key)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        topics.append(item)
                    elif isinstance(item, dict):
                        t = item.get("title") or item.get("topic") or item.get("pillar") or item.get("idea")
                        if t:
                            topics.append(str(t))
                        for cp in (item.get("content_pieces") or []):
                            if isinstance(cp, dict) and cp.get("title"):
                                topics.append(str(cp["title"]))
            if topics:
                break
    seen, out = set(), []
    for t in topics:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


async def run_cycle(db, user: User, *, count: int = 3) -> TeamRun:
    key = resolve_hub_key(user)
    if not key:
        raise TeamError("AI is temporarily unavailable. Please try again.")
    acct = await db.scalar(
        select(LinkedInAccount).where(LinkedInAccount.user_id == user.id).order_by(LinkedInAccount.id)
    )
    if not acct:
        raise TeamError("Connect a channel first, then run your content team.")
    if not credits.has_credits(user, 1):
        raise TeamError("You're out of credits for now. Subscribe for more, or come back tomorrow.", 402)

    platform = acct.platform or "linkedin"
    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == user.id))
    audience = (brand.audience if brand else None) or "your audience"
    voice = (brand.voice if brand else None) or "professional but human"
    seed = (brand and (brand.industry or brand.brand_name)) or "your industry"

    # --- Strategist: a content strategy → topics + brief ---
    brief, topics = None, []
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            strat = await hub.call("content_strategy", {
                "topic": seed, "audience": audience, "timeframe": "this week",
            })
            if isinstance(strat, dict):
                brief = strat.get("summary") or strat.get("overview")
            topics = _topics_from_strategy(strat, count)
        except HubError as e:
            log.warning("Team strategist failed: %s", getattr(e, "message", e))
    if not topics:
        topics = [f"{seed}: angle #{i + 1}" for i in range(count)]
    if not brief:
        brief = f"This week's focus: consistent, on-brand content for {audience}."

    run = TeamRun(user_id=user.id, status=team_status.DRAFT, brief=str(brief))
    db.add(run)
    await db.commit()
    await db.refresh(run)

    made = 0
    async with HubClient(settings.hub_base_url, key) as hub:
        for i in range(count):
            if not credits.has_credits(user, 1):
                break
            topic = topics[i % len(topics)]
            try:
                data = await hub.generate_text_post(
                    topic=topic, post_type="Personal Story + Lesson",
                    audience=audience, tone=voice, include_cta="question to comments",
                )
            except HubError as e:
                log.warning("Team writer skipped a post: %s", getattr(e, "message", e))
                continue
            body = (data.get("full_post") or data.get("post") or data.get("content") or "").strip()
            if not body:
                continue
            hashtags = data.get("hashtags") if isinstance(data.get("hashtags"), list) else None
            score = None
            try:
                qa = await hub.call("score_checker", {"content": body, "platform": platform})
                if isinstance(qa, dict):
                    raw = qa.get("score") or qa.get("overall_score") or qa.get("quality_score")
                    score = int(raw) if raw is not None else None
            except (HubError, ValueError, TypeError):
                score = None
            db.add(Post(
                user_id=user.id, account_id=acct.id, platform=platform, body=body,
                hashtags=hashtags, status=post_status.DRAFT, source="generated",
                team_run_id=run.id, qa_score=score,
            ))
            await credits.charge(db, user, 1)  # commits the pending post too
            made += 1

    if made == 0:
        raise TeamError("The team couldn't draft content right now. Please try again shortly.", 502)
    await db.refresh(run)
    return run


async def approve_run(db, user: User, run_id: int):
    """Schedule a run's draft posts across the coming days. Returns (run, n, errors)."""
    run = await db.get(TeamRun, run_id)
    if not run or run.user_id != user.id:
        raise TeamError("Run not found.", 404)
    zkey = resolve_zernio_key(user)
    if not zkey:
        raise TeamError("Connect your channels first.", 400)
    posts = list(await db.scalars(
        select(Post).where(Post.team_run_id == run.id, Post.status == post_status.DRAFT).order_by(Post.id)
    ))
    if not posts:
        raise TeamError("Nothing left to schedule in this run.", 400)

    # One per day at 09:00 UTC, starting tomorrow.
    base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    acct_cache: dict[int, LinkedInAccount] = {}
    scheduled, errors = 0, []
    for idx, post in enumerate(posts):
        acct = acct_cache.get(post.account_id) or await db.get(LinkedInAccount, post.account_id)
        acct_cache[post.account_id] = acct
        try:
            await publisher.schedule(
                post, acct.zernio_account_id, base + timedelta(days=idx), "UTC",
                platform=post.platform, zernio_key=zkey,
            )
            scheduled += 1
        except publisher.PublishError as e:
            errors.append(e.message)
    run.status = team_status.SCHEDULED
    await db.commit()
    await db.refresh(run)
    return run, scheduled, errors
