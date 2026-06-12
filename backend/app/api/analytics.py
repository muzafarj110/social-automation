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

_METRIC_KEYS = ("impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views")


def _aggregate(zdata: dict) -> dict:
    """Roll Zernio's per-post analytics into account totals/averages.

    Zernio shape: {overview:{publishedPosts,...}, posts:[{content, status,
    analytics:{impressions,likes,...}, platforms:[{platformPostUrl,...}]}]}.
    """
    overview = zdata.get("overview") or {}
    posts = zdata.get("posts") or []
    totals = {k: 0 for k in _METRIC_KEYS}
    recent = []
    for p in posts:
        a = p.get("analytics") or {}
        for k in _METRIC_KEYS:
            try:
                totals[k] += int(a.get(k) or 0)
            except (TypeError, ValueError):
                pass
        url = None
        plats = p.get("platforms") or []
        if plats and isinstance(plats[0], dict):
            url = plats[0].get("platformPostUrl")
        recent.append({
            "content": (p.get("content") or "")[:160],
            "status": p.get("status"),
            "impressions": (p.get("analytics") or {}).get("impressions", 0),
            "likes": (p.get("analytics") or {}).get("likes", 0),
            "comments": (p.get("analytics") or {}).get("comments", 0),
            "url": url,
        })
    n = len(posts)
    post_count = overview.get("publishedPosts") or overview.get("totalPosts") or n
    denom = n or 1
    return {
        "post_count": post_count,
        "impressions": totals["impressions"],
        "reach": totals["reach"],
        "total_likes": totals["likes"],
        "total_comments": totals["comments"],
        "total_shares": totals["shares"],
        "avg_likes": round(totals["likes"] / denom),
        "avg_comments": round(totals["comments"] / denom),
        "avg_shares": round(totals["shares"] / denom),
        "recent": recent[:25],
    }


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
            data = await z.get_analytics(platform="linkedin")
        except ZernioError as e:
            return {"ok": False, "error": e.message}
    return {"ok": True, "summary": _aggregate(data), "data": data}


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
