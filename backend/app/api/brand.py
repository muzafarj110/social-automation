"""
Brand API — the strategy brain. Stores one BrandProfile per user (voice,
persona, positioning) and runs the Hub's strategy models to build it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.hub_client import HubClient, HubError
from app.core.config import settings
from app.core.hub_errors import hub_http
from app.core.user_keys import resolve_hub_key
from app.db.session import get_db
from app.models.brand import BrandProfile
from app.models.user import User
from app.schemas.brand import BrandGenerateRequest, BrandProfileOut, BrandProfileUpdate

router = APIRouter(prefix="/brand", tags=["brand"])


async def _get_or_create(user: User, db: AsyncSession) -> BrandProfile:
    bp = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == user.id))
    if bp is None:
        bp = BrandProfile(user_id=user.id)
        db.add(bp)
        await db.commit()
        await db.refresh(bp)
    return bp


@router.get("", response_model=BrandProfileOut)
async def get_brand(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandProfile:
    return await _get_or_create(current, db)


@router.put("", response_model=BrandProfileOut)
async def update_brand(
    body: BrandProfileUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandProfile:
    bp = await _get_or_create(current, db)
    data = body.model_dump(exclude_unset=True)
    # merge docs rather than replace, so saving one artifact keeps the others
    if "docs" in data and data["docs"] is not None:
        merged = dict(bp.docs or {})
        merged.update(data.pop("docs"))
        bp.docs = merged
    for field, value in data.items():
        setattr(bp, field, value)
    await db.commit()
    await db.refresh(bp)
    return bp


@router.post("/generate")
async def generate(
    body: BrandGenerateRequest,
    current: User = Depends(get_current_user),
) -> dict[str, object]:
    """Run a Hub strategy model (brand voice, persona, UVP, etc.)."""
    key = resolve_hub_key(current)
    if not key:
        raise HTTPException(400, "AI is temporarily unavailable. Please try again.")
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.call(body.tool, body.params)
        except HubError as e:
            raise hub_http(e) from e
    return {"ok": True, "data": data}
