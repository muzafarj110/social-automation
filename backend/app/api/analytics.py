"""
Analytics API — the feedback loop.

Reads LinkedIn metrics from Zernio and interprets them with the Hub's analytics /
viral-analyzer models, so the insights can guide what the autopilot posts next.
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
from app.clients.zernio_client import ZernioClient, ZernioError
from app.core.config import settings
from app.core.user_keys import resolve_hub_key, resolve_zernio_key
from app.models.user import User
from app.schemas.analytics import InsightsRequest, ViralRequest

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _hub_key_or_400(user: User) -> str:
    key = resolve_hub_key(user)
    if not key:
        raise HTTPException(400, "No Hub API key on file — set one in the app first.")
    return key


async def _hub_call(user: User, name: str, payload: dict) -> dict:
    async with HubClient(settings.hub_base_url, _hub_key_or_400(user)) as hub:
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


@router.get("/zernio")
async def zernio_metrics(current: User = Depends(get_current_user)) -> dict:
    """Raw LinkedIn metrics from the user's Zernio account (best-effort)."""
    key = resolve_zernio_key(current)
    if not key:
        raise HTTPException(400, "Set your Zernio API key in the app first.")
    async with ZernioClient(settings.zernio_base_url, key) as z:
        try:
            return {"ok": True, "data": await z.get_analytics(platform="linkedin")}
        except ZernioError as e:
            return {"ok": False, "error": e.message}


@router.post("/insights")
async def insights(
    body: InsightsRequest, current: User = Depends(get_current_user)
) -> dict:
    """Interpret account metrics via the Hub's analytics model."""
    data = await _hub_call(current, "analytics", body.model_dump(exclude_none=True))
    return {"ok": True, "data": data}


@router.post("/viral")
async def viral(
    body: ViralRequest, current: User = Depends(get_current_user)
) -> dict:
    """Analyze one post's reach/engagement via the Hub's viral-analyzer."""
    data = await _hub_call(current, "viral_analyzer", body.model_dump(exclude_none=True))
    return {"ok": True, "data": data}
