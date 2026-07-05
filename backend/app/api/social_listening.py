"""
Social Listening API — surface high-intent prospects and reputation signals.

Users track keywords/topics. Each AI scan (1 credit) uses the Hub
engagement_strategy model to surface conversation signals, prospect patterns,
and recommended engagement actions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.hub_client import HubClient, HubError
from app.core import credits
from app.core.config import settings
from app.core.hub_errors import hub_http
from app.core.user_keys import resolve_hub_key
from app.db.session import get_db
from app.models.brand import BrandProfile
from app.models.social_listening import ListeningTopic
from app.models.user import User
from app.schemas.social_listening import TopicCreate, TopicOut, TopicUpdate

router = APIRouter(prefix="/listening", tags=["listening"])


def _coerce_list(value) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        parts = [p.strip(" -•\t") for p in value.replace("\r", "\n").split("\n")]
        out = [p for p in parts if p]
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                txt = (item.get("title") or item.get("name") or item.get("signal")
                       or item.get("action") or item.get("text") or item.get("tactic"))
                if txt:
                    desc = item.get("description") or item.get("detail") or item.get("why")
                    out.append(f"{txt} — {desc}" if desc else str(txt))
    return out[:8]


def _parse_results(data: dict) -> dict:
    """Extract {summary, signals[], actions[]} from Hub response."""
    if not isinstance(data, dict):
        return {"summary": "", "signals": [], "actions": []}

    summary = ""
    for k in ("summary", "overview", "strategy", "insights", "analysis", "recommendation"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            summary = v.strip()
            break

    signals: list[str] = []
    for k in ("signals", "prospects", "opportunities", "high_intent", "conversations",
              "engagement_opportunities", "tactics", "insights", "content_ideas"):
        signals = _coerce_list(data.get(k))
        if signals:
            break

    actions: list[str] = []
    for k in ("actions", "recommendations", "next_steps", "engagement_actions",
              "strategies", "content_recommendations"):
        actions = _coerce_list(data.get(k))
        if actions:
            break

    return {"summary": summary, "signals": signals, "actions": actions}


def _serialize(t: ListeningTopic) -> dict:
    results = None
    if t.results:
        try:
            results = json.loads(t.results)
        except (ValueError, TypeError):
            results = None
    return {
        "id": t.id, "keyword": t.keyword, "description": t.description,
        "platform": t.platform, "results": results,
        "scanned_at": t.scanned_at, "created_at": t.created_at,
    }


async def _owned(tid: int, user: User, db: AsyncSession) -> ListeningTopic:
    t = await db.get(ListeningTopic, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    return t


@router.get("", response_model=list[TopicOut])
async def list_topics(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.scalars(
        select(ListeningTopic)
        .where(ListeningTopic.user_id == current.id)
        .order_by(ListeningTopic.created_at.desc())
    )
    return [_serialize(t) for t in rows]


@router.post("", response_model=TopicOut, status_code=201)
async def create_topic(
    body: TopicCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = ListeningTopic(user_id=current.id, **body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.patch("/{tid}", response_model=TopicOut)
async def update_topic(
    tid: int,
    body: TopicUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = await _owned(tid, current, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.delete("/{tid}", status_code=204, response_model=None)
async def delete_topic(
    tid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    t = await _owned(tid, current, db)
    await db.delete(t)
    await db.commit()


@router.post("/{tid}/scan", response_model=TopicOut)
async def scan_topic(
    tid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run an AI social listening scan (1 credit)."""
    t = await _owned(tid, current, db)
    if not credits.has_credits(current, credits.COST_GENERATE):
        raise HTTPException(402, "You're out of credits. Top up under Billing to keep scanning.")
    key = resolve_hub_key(current)
    if not key:
        raise HTTPException(400, "AI is temporarily unavailable. Please try again.")

    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == current.id))
    my_brand = (brand.brand_name if brand else None) or "my brand"
    audience = (brand.audience if brand else None) or "B2B professionals"
    niche = (brand.industry if brand else None) or t.platform

    bits = [
        f"Social listening strategy for keyword: '{t.keyword}' on {t.platform}.",
        f"Brand: {my_brand}. Target audience: {audience}.",
    ]
    if t.description:
        bits.append(f"Context: {t.description}.")
    bits.append(
        "Identify the high-intent signals and conversation patterns around this topic, "
        "prospect types most likely to be buyers, and specific engagement actions "
        "to build authority, find leads, and protect brand reputation."
    )
    payload = {
        "topic": " ".join(bits),
        "audience": audience,
        "niche": niche,
        "goal": "find high-intent prospects and surface engagement opportunities",
    }

    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.call("engagement_strategy", payload)
        except HubError as e:
            raise hub_http(e) from e

    results = _parse_results(data if isinstance(data, dict) else {})
    if not (results["summary"] or results["signals"] or results["actions"]):
        results["summary"] = "Scan complete but returned no structured insights — try adding more context about what you're looking for."

    t.results = json.dumps(results)
    t.scanned_at = datetime.now(timezone.utc)
    await credits.charge(db, current, credits.COST_GENERATE)
    await db.refresh(t)
    return _serialize(t)
