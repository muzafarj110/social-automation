"""
Proactive feed generation — agents auto-fill the Live Work Feed.

Called on a background schedule (every 30 min). For each active user:
  1. Pull insights from data they've already built (competitors, listening,
     SEO projects, leads) — zero credit cost. If more than one of these tiers
     has fresh data, one is picked at random so the feed doesn't always favor
     whichever tier happens to be checked first.
  2. Fall back to Hub `viral_hook` for a fresh content tip (1 credit).
  3. Fall back to static nudges if the user hasn't set anything up yet.

At most 2 new items are generated per user per 6-hour window so the feed
stays fresh without being overwhelming.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.hub_client import HubClient, HubError
from app.core import credits
from app.core.config import settings
from app.core.user_keys import resolve_hub_key
from app.models.brand import BrandProfile
from app.models.competitor import Competitor
from app.models.lead import CONTACTED, NEW, Lead
from app.models.proactive import ProactiveItem
from app.models.seo_geo import SeoProject
from app.models.social_listening import ListeningTopic
from app.models.user import User

log = logging.getLogger("uvicorn.error")

MAX_PER_WINDOW = 2
WINDOW_HOURS = 6

# Static nudges shown when a user has no data to pull from yet.
NUDGES = [
    ("content", "Your content agent is standing by",
     "Tell your content agent your goal for the week and they'll draft posts, hooks and headlines.", "team"),
    ("competitor", "Track a competitor to unlock automatic positioning insights",
     "Add a rival and your competitor agent will analyze their tactics and surface gaps you can exploit.", "competitor"),
    ("listening", "Your listening agent can find high-intent prospects right now",
     "Add a keyword or topic to start surfacing buyers who are actively looking for what you offer.", "listening"),
    ("leadgen", "Lead-gen agent is ready to start drafting outreach",
     "Add a prospect and let AI draft a personalised message — you approve before anything sends.", "leads"),
]


async def generate_for_user(user: User, db: AsyncSession) -> ProactiveItem | None:
    """Generate one proactive feed item for a user. Returns the item or None."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    recent = await db.scalar(
        select(func.count(ProactiveItem.id))
        .where(ProactiveItem.user_id == user.id)
        .where(ProactiveItem.generated_at > cutoff)
        .where(ProactiveItem.status != "dismissed")
    )
    if recent >= MAX_PER_WINDOW:
        return None

    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == user.id))
    brand_name = (brand.brand_name if brand else None) or "your brand"
    audience = (brand.audience if brand else None) or "B2B professionals"
    industry = (brand.industry if brand else None) or "technology"

    # --- 1-4. Data-backed tiers (free) -----------------------------------------
    # Each tier is a non-destructive read. Every tier that has fresh data to
    # offer contributes one (agent, title, body, action_tab) candidate; we then
    # pick a single winner at random so the feed doesn't always favor whichever
    # tier happens to be checked first.
    tier_candidates: list[tuple[str, str, str, str]] = []

    # --- Competitor insight -----------------------------------------------
    competitor = await db.scalar(
        select(Competitor)
        .where(Competitor.user_id == user.id)
        .where(Competitor.analysis.is_not(None))
        .order_by(func.random())
        .limit(1)
    )
    if competitor:
        try:
            analysis = json.loads(competitor.analysis)
            tactics = analysis.get("tactics") or []
            if tactics:
                tip = tactics[0] if isinstance(tactics[0], str) else str(tactics[0])
                tier_candidates.append((
                    "competitor",
                    f"{competitor.name} is using a tactic worth copying",
                    tip,
                    "competitor",
                ))
        except (ValueError, TypeError, IndexError):
            pass

    # --- Social listening insight -------------------------------------------
    topic = await db.scalar(
        select(ListeningTopic)
        .where(ListeningTopic.user_id == user.id)
        .where(ListeningTopic.results.is_not(None))
        .order_by(func.random())
        .limit(1)
    )
    if topic:
        try:
            results = json.loads(topic.results)
            signals = results.get("signals") or []
            if signals:
                sig = signals[0] if isinstance(signals[0], str) else str(signals[0])
                tier_candidates.append((
                    "listening",
                    f"High-intent signal around '{topic.keyword}'",
                    sig,
                    "listening",
                ))
        except (ValueError, TypeError, IndexError):
            pass

    # --- SEO keyword tip ------------------------------------------------------
    project = await db.scalar(
        select(SeoProject)
        .where(SeoProject.user_id == user.id)
        .where(SeoProject.results.is_not(None))
        .order_by(func.random())
        .limit(1)
    )
    if project:
        try:
            results = json.loads(project.results)
            keywords = results.get("keywords") or []
            if keywords:
                kw = keywords[0] if isinstance(keywords[0], str) else str(keywords[0])
                tier_candidates.append((
                    "seo",
                    "Keyword opportunity your content agent should target",
                    kw,
                    "seo",
                ))
        except (ValueError, TypeError, IndexError):
            pass

    # --- Lead-gen outreach ------------------------------------------------
    lead = await db.scalar(
        select(Lead)
        .where(Lead.user_id == user.id)
        .where(Lead.status.in_([NEW, CONTACTED]))
        .where(Lead.draft.is_not(None))
        .order_by(Lead.updated_at.desc())
        .limit(1)
    )
    if lead:
        tier_candidates.append((
            "leadgen",
            "Lead-gen agent drafted outreach ready to send",
            f"Outreach for {lead.name} is drafted and waiting in Leads — copy it and send when ready.",
            "leads",
        ))
    else:
        new_lead_count = await db.scalar(
            select(func.count(Lead.id))
            .where(Lead.user_id == user.id)
            .where(Lead.status == NEW)
            .where(Lead.draft.is_(None))
        )
        if new_lead_count:
            tier_candidates.append((
                "leadgen",
                "Lead-gen agent can draft outreach for your new prospects",
                f"You have {new_lead_count} new lead{'s' if new_lead_count != 1 else ''} without a drafted message yet.",
                "leads",
            ))

    if tier_candidates:
        agent, title, body, tab = random.choice(tier_candidates)
        return await _save(db, user.id, agent, title, body, tab)

    # --- 5. Hub: viral content hook (1 credit) --------------------------------
    key = resolve_hub_key(user)
    if key and credits.has_credits(user, credits.COST_GENERATE):
        try:
            async with HubClient(settings.hub_base_url, key) as hub:
                data = await hub.call("viral_hook", {
                    "topic": f"{industry} insights for {audience}",
                    "audience": audience,
                })
            hook = (data.get("hook") or data.get("viral_hook") or
                    data.get("text") or data.get("headline") or "")
            if isinstance(hook, list):
                hook = hook[0] if hook else ""
            hook = str(hook).strip()
            if hook:
                await credits.charge(db, user, credits.COST_GENERATE)
                return await _save(db, user.id, "content",
                    "Your content agent drafted a hook worth publishing",
                    hook, "team")
        except (HubError, Exception) as exc:
            log.debug("Proactive hub call failed for user %s: %s", user.id, exc)

    # --- 6. Static nudge (always available) -----------------------------------
    # Pick one we haven't shown recently
    shown_agents: set[str] = set()
    recent_rows = await db.scalars(
        select(ProactiveItem.agent)
        .where(ProactiveItem.user_id == user.id)
        .where(ProactiveItem.generated_at > cutoff)
    )
    shown_agents = set(recent_rows)

    candidates = [n for n in NUDGES if n[0] not in shown_agents]
    if not candidates:
        candidates = NUDGES  # all shown — just rotate

    agent_key, title, body, tab = random.choice(candidates)
    return await _save(db, user.id, agent_key, title, body, tab)


async def _save(
    db: AsyncSession, user_id: int, agent: str, title: str, body: str, action_tab: str
) -> ProactiveItem:
    item = ProactiveItem(
        user_id=user_id, agent=agent, title=title, body=body, action_tab=action_tab
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
