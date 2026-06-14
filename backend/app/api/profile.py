"""
Profile Studio API — optimize the user's LinkedIn profile via Hub models.
All read-only generation (no posting); uses the logged-in user's Hub key.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.clients.hub_client import HubClient, HubError
from app.core.config import settings
from app.core.hub_errors import hub_http
from app.core.user_keys import resolve_hub_key
from app.models.user import User
from app.schemas.profile import (
    FeaturedSectionRequest,
    HeadlineVariantsRequest,
    ProfileOptimizeRequest,
    RecommendationRequest,
)

router = APIRouter(prefix="/profile-studio", tags=["profile"])


async def _call(user: User, name: str, payload: dict) -> dict:
    key = resolve_hub_key(user)
    if not key:
        raise HTTPException(400, "AI is temporarily unavailable. Please try again.")
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            return await hub.call(name, payload)
        except HubError as e:
            raise hub_http(e) from e


@router.post("/optimize")
async def optimize(req: ProfileOptimizeRequest, current: User = Depends(get_current_user)) -> dict:
    return {"ok": True, "data": await _call(current, "profile_optimizer", req.model_dump(exclude_none=True))}


@router.post("/headlines")
async def headlines(req: HeadlineVariantsRequest, current: User = Depends(get_current_user)) -> dict:
    return {"ok": True, "data": await _call(current, "headline_variants", req.model_dump(exclude_none=True))}


@router.post("/featured")
async def featured(req: FeaturedSectionRequest, current: User = Depends(get_current_user)) -> dict:
    return {"ok": True, "data": await _call(current, "featured_section", req.model_dump(exclude_none=True))}


@router.post("/recommendation")
async def recommendation(req: RecommendationRequest, current: User = Depends(get_current_user)) -> dict:
    return {"ok": True, "data": await _call(current, "recommendation", req.model_dump(exclude_none=True))}
