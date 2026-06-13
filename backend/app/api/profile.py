"""
Profile Studio API — optimize the user's LinkedIn profile via Hub models.
All read-only generation (no posting); uses the logged-in user's Hub key.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.clients.hub_client import (
    HubAuthError,
    HubClient,
    HubError,
    HubPermissionError,
    HubRateLimitError,
)
from app.core.config import settings
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
        raise HTTPException(400, "No Hub API key on file — set one in the app first.")
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            return await hub.call(name, payload)
        except HubRateLimitError as e:
            raise HTTPException(429, e.message) from e
        except HubAuthError as e:
            raise HTTPException(401, e.message) from e
        except HubPermissionError as e:
            raise HTTPException(403, e.message) from e
        except HubError as e:
            raise HTTPException(502, f"Hub error: {e.message}") from e


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
