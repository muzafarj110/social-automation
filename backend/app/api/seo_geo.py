"""
SEO + GEO API — keyword research and Generative Engine Optimization.

SEO: surface keyword opportunities the user should target.
GEO (Generative Engine Optimization): surface how to get mentioned in AI
chatbot answers (ChatGPT, Perplexity, Claude). One combined analysis per
project (2 credits: keyword_research + technical_seo).
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
from app.models.seo_geo import SeoProject
from app.models.user import User
from app.schemas.seo_geo import SeoProjectCreate, SeoProjectOut, SeoProjectUpdate

router = APIRouter(prefix="/seo", tags=["seo"])


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
                txt = (item.get("keyword") or item.get("title") or item.get("name")
                       or item.get("text") or item.get("recommendation"))
                if txt:
                    desc = (item.get("intent") or item.get("volume") or item.get("difficulty")
                            or item.get("description") or item.get("detail"))
                    out.append(f"{txt} — {desc}" if desc else str(txt))
    return out[:10]


def _parse_seo(data: dict) -> dict:
    """Extract {summary, keywords[], geo[], technical[]} from Hub responses."""
    if not isinstance(data, dict):
        return {"summary": "", "keywords": [], "geo": [], "technical": []}

    summary = ""
    for k in ("summary", "overview", "analysis", "strategy", "insights"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            summary = v.strip()
            break

    keywords: list[str] = []
    for k in ("keywords", "keyword_opportunities", "target_keywords", "long_tail_keywords",
              "primary_keywords", "opportunities", "recommendations"):
        keywords = _coerce_list(data.get(k))
        if keywords:
            break

    geo: list[str] = []
    for k in ("geo_recommendations", "ai_optimization", "geo", "generative_engine",
              "content_recommendations", "content_strategy", "topics"):
        geo = _coerce_list(data.get(k))
        if geo:
            break

    technical: list[str] = []
    for k in ("technical", "technical_recommendations", "fixes", "improvements",
              "technical_seo", "actions", "next_steps"):
        technical = _coerce_list(data.get(k))
        if technical:
            break

    return {"summary": summary, "keywords": keywords, "geo": geo, "technical": technical}


def _merge_results(seo_data: dict, tech_data: dict) -> dict:
    """Merge keyword_research and technical_seo responses into one results dict."""
    base = _parse_seo(seo_data)

    # Pull technical items from technical_seo response if base is empty
    if not base["technical"] and isinstance(tech_data, dict):
        tech_parsed = _parse_seo(tech_data)
        base["technical"] = tech_parsed["technical"] or tech_parsed["keywords"]

    # Pull GEO hints from technical_seo (it often has content strategy)
    if not base["geo"] and isinstance(tech_data, dict):
        tech_parsed = _parse_seo(tech_data)
        base["geo"] = tech_parsed["geo"] or tech_parsed["keywords"]

    if not base["summary"] and isinstance(tech_data, dict):
        for k in ("summary", "overview", "analysis"):
            v = tech_data.get(k)
            if isinstance(v, str) and v.strip():
                base["summary"] = v.strip()
                break

    return base


def _serialize(p: SeoProject) -> dict:
    results = None
    if p.results:
        try:
            results = json.loads(p.results)
        except (ValueError, TypeError):
            results = None
    return {
        "id": p.id, "website": p.website, "target_keywords": p.target_keywords,
        "audience": p.audience, "results": results,
        "analyzed_at": p.analyzed_at, "created_at": p.created_at,
    }


async def _owned(pid: int, user: User, db: AsyncSession) -> SeoProject:
    p = await db.get(SeoProject, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return p


@router.get("", response_model=list[SeoProjectOut])
async def list_projects(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.scalars(
        select(SeoProject)
        .where(SeoProject.user_id == current.id)
        .order_by(SeoProject.created_at.desc())
    )
    return [_serialize(p) for p in rows]


@router.post("", response_model=SeoProjectOut, status_code=201)
async def create_project(
    body: SeoProjectCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    p = SeoProject(user_id=current.id, **body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _serialize(p)


@router.patch("/{pid}", response_model=SeoProjectOut)
async def update_project(
    pid: int,
    body: SeoProjectUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    p = await _owned(pid, current, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    await db.commit()
    await db.refresh(p)
    return _serialize(p)


@router.delete("/{pid}", status_code=204, response_model=None)
async def delete_project(
    pid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    p = await _owned(pid, current, db)
    await db.delete(p)
    await db.commit()


@router.post("/{pid}/analyze", response_model=SeoProjectOut)
async def analyze_project(
    pid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run keyword research + technical SEO + GEO analysis (2 credits)."""
    p = await _owned(pid, current, db)
    cost = credits.COST_LONG_FORM
    if not credits.has_credits(current, cost):
        raise HTTPException(402, "You need at least 2 credits for a full SEO + GEO analysis. Top up under Billing.")
    key = resolve_hub_key(current)
    if not key:
        raise HTTPException(400, "AI is temporarily unavailable. Please try again.")

    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == current.id))
    my_brand = (brand.brand_name if brand else None) or "my brand"
    audience = p.audience or (brand.audience if brand else None) or "B2B professionals"

    seo_bits = [
        f"Keyword research for {my_brand}.",
        f"Website: {p.website}." if p.website else "",
        f"Target keywords / topics: {p.target_keywords}.",
        f"Audience: {audience}.",
        "Find the best keyword opportunities, long-tail terms, and content gaps "
        "that will drive organic traffic and establish topical authority. "
        "Also include GEO (Generative Engine Optimization) recommendations — "
        "how to get this brand mentioned and cited in AI chatbot answers "
        "(ChatGPT, Perplexity, Claude, Gemini).",
    ]
    tech_bits = [
        f"Technical SEO and content strategy for {my_brand}.",
        f"Website: {p.website}." if p.website else "",
        f"Focus keywords: {p.target_keywords}.",
        f"Audience: {audience}.",
        "Identify the most impactful technical SEO improvements and content "
        "structure recommendations to improve rankings and AI chatbot visibility.",
    ]

    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            seo_data = await hub.call(
                "keyword_research",
                {"topic": " ".join(b for b in seo_bits if b), "audience": audience},
            )
        except HubError as e:
            raise hub_http(e) from e
        try:
            tech_data = await hub.call(
                "technical_seo",
                {
                    "target": " ".join(b for b in tech_bits if b),
                    "primary_keyword": p.target_keywords,
                },
            )
        except HubError as e:
            # technical_seo is secondary; if it fails, continue with SEO data only.
            tech_data = {}

    results = _merge_results(
        seo_data if isinstance(seo_data, dict) else {},
        tech_data if isinstance(tech_data, dict) else {},
    )
    if not any(results.values()):
        results["summary"] = "Analysis ran but returned no structured data — try adding more context."

    p.results = json.dumps(results)
    p.analyzed_at = datetime.now(timezone.utc)
    await credits.charge(db, current, cost)
    await db.refresh(p)
    return _serialize(p)
