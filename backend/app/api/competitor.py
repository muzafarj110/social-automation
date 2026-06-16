"""
Competitor Strategy API — the competitor-watch agent.

Track rivals and run an AI analysis (via the Hub `competitor_analysis` model) that
surfaces tactics worth copying and positioning gaps to exploit. Analysis is a
billed AI action (one credit). Every record is owner-scoped.
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
from app.models.competitor import Competitor
from app.models.user import User
from app.schemas.competitor import CompetitorCreate, CompetitorOut, CompetitorUpdate

router = APIRouter(prefix="/competitors", tags=["competitors"])


def _coerce_list(value) -> list[str]:
    """Normalize a Hub field into a clean list of short strings."""
    out: list[str] = []
    if isinstance(value, str):
        # split on newlines / bullets if it's one blob
        parts = [p.strip(" -•\t") for p in value.replace("\r", "\n").split("\n")]
        out = [p for p in parts if p]
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                txt = item.get("title") or item.get("name") or item.get("text") or item.get("tactic") or item.get("gap")
                if txt:
                    desc = item.get("description") or item.get("detail") or item.get("why")
                    out.append(f"{txt} — {desc}" if desc else str(txt))
    return out[:8]


def _parse_analysis(data: dict) -> dict:
    """Pull {summary, tactics[], gaps[]} out of a flexible Hub response."""
    if not isinstance(data, dict):
        return {"summary": "", "tactics": [], "gaps": []}
    summary = ""
    for k in ("summary", "overview", "analysis", "headline", "positioning"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            summary = v.strip()
            break
    tactics: list[str] = []
    for k in ("tactics", "winning_tactics", "opportunities", "strengths", "what_works", "ideas"):
        tactics = _coerce_list(data.get(k))
        if tactics:
            break
    gaps: list[str] = []
    for k in ("gaps", "weaknesses", "positioning_gaps", "recommendations", "openings", "where_to_win"):
        gaps = _coerce_list(data.get(k))
        if gaps:
            break
    return {"summary": summary, "tactics": tactics, "gaps": gaps}


def _serialize(c: Competitor) -> dict:
    analysis = None
    if c.analysis:
        try:
            analysis = json.loads(c.analysis)
        except (ValueError, TypeError):
            analysis = None
    return {
        "id": c.id, "name": c.name, "website": c.website, "notes": c.notes,
        "analysis": analysis, "analyzed_at": c.analyzed_at, "created_at": c.created_at,
    }


async def _owned(cid: int, user: User, db: AsyncSession) -> Competitor:
    c = await db.get(Competitor, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Competitor not found")
    return c


@router.get("", response_model=list[CompetitorOut])
async def list_competitors(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.scalars(
        select(Competitor).where(Competitor.user_id == current.id).order_by(Competitor.created_at.desc())
    )
    return [_serialize(c) for c in rows]


@router.post("", response_model=CompetitorOut, status_code=201)
async def create_competitor(
    body: CompetitorCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    c = Competitor(user_id=current.id, **body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)


@router.patch("/{cid}", response_model=CompetitorOut)
async def update_competitor(
    cid: int,
    body: CompetitorUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    c = await _owned(cid, current, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)


@router.delete("/{cid}", status_code=204, response_model=None)
async def delete_competitor(
    cid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    c = await _owned(cid, current, db)
    await db.delete(c)
    await db.commit()


@router.post("/{cid}/analyze", response_model=CompetitorOut)
async def analyze_competitor(
    cid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run an AI competitor analysis (1 credit) and store the result."""
    c = await _owned(cid, current, db)
    if not credits.has_credits(current, credits.COST_GENERATE):
        raise HTTPException(402, "You're out of credits. Top up under Billing to keep analyzing.")
    key = resolve_hub_key(current)
    if not key:
        raise HTTPException(400, "AI is temporarily unavailable. Please try again.")

    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == current.id))
    my_brand = (brand.brand_name if brand else None) or "my brand"

    # Hub `competitor_analysis` takes {topic (req), depth, focus}. We pack the
    # competitor, site and notes plus our brand into a rich topic string.
    bits = [f"Competitor analysis of {c.name}"]
    if c.website:
        bits.append(f"(website: {c.website})")
    bits.append(f"compared to {my_brand}.")
    if c.notes:
        bits.append(f"Context: {c.notes}")
    bits.append("Identify winning tactics worth copying and positioning gaps we can exploit.")
    payload = {"topic": " ".join(bits), "depth": "deep", "focus": "all"}
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.call("competitor_analysis", payload)
        except HubError as e:
            raise hub_http(e) from e

    analysis = _parse_analysis(data if isinstance(data, dict) else {})
    if not (analysis["summary"] or analysis["tactics"] or analysis["gaps"]):
        analysis["summary"] = "Analysis ran but returned no structured insights — try adding more notes."
    c.analysis = json.dumps(analysis)
    c.analyzed_at = datetime.now(timezone.utc)
    await credits.charge(db, current, credits.COST_GENERATE)
    await db.refresh(c)
    return _serialize(c)
