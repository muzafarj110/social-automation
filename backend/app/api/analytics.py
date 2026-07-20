"""
Analytics API — the feedback loop.

Reads LinkedIn metrics from Zernio and interprets them with the Hub's analytics /
viral-analyzer models, so the insights can guide what the autopilot posts next.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.hub_client import HubClient, HubError
from app.clients.zernio_client import ZernioClient, ZernioError
from app.core.config import settings
from app.core.hub_errors import hub_http
from app.core.user_keys import is_white_label, resolve_hub_key, resolve_zernio_key
from app.db.session import get_db
from app.models.account import LinkedInAccount
from app.models.user import User
from app.schemas.analytics import InsightsRequest, ViralRequest
from app.services.channels import ensure_profile

router = APIRouter(prefix="/analytics", tags=["analytics"])
log = logging.getLogger("uvicorn.error")

_METRIC_KEYS = ("impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views")

# Platforms that report reach as "views" rather than "impressions" — showing
# a video platform's real view count under an "Impressions" label (or vice
# versa) misrepresents what was actually measured.
VIEW_BASED_PLATFORMS = {"youtube", "tiktok"}


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
        platform = (p.get("platform") or "").lower()
        post_analytics = p.get("analytics") or {}
        # The metric that actually reflects reach for this post's platform —
        # views for YouTube/TikTok, impressions for everything else — so a
        # per-post number is never silently 0 just because it was captured
        # under a differently-named field.
        reach_value = post_analytics.get("views" if platform in VIEW_BASED_PLATFORMS else "impressions", 0)
        recent.append({
            "content": (p.get("content") or "")[:160],
            "status": p.get("status"),
            "platform": p.get("platform"),
            "impressions": post_analytics.get("impressions", 0),
            "views": post_analytics.get("views", 0),
            "reach_value": reach_value,
            "likes": post_analytics.get("likes", 0),
            "comments": post_analytics.get("comments", 0),
            "url": url,
        })
    n = len(posts)
    post_count = overview.get("publishedPosts") or overview.get("totalPosts") or n
    denom = n or 1
    return {
        "post_count": post_count,
        "impressions": totals["impressions"],
        "views": totals["views"],
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
        raise HTTPException(400, "AI is temporarily unavailable. Please try again.")
    return key


async def _hub_call(user: User, name: str, payload: dict) -> dict:
    async with HubClient(settings.hub_base_url, _hub_key_or_400(user)) as hub:
        try:
            return await hub.call(name, payload)
        except HubError as e:
            raise hub_http(e) from e


async def connected_platforms(user: User, db: AsyncSession) -> list[str]:
    """The distinct platforms the user has connected accounts on (default LinkedIn)."""
    rows = await db.scalars(
        select(LinkedInAccount.platform).where(LinkedInAccount.user_id == user.id).distinct()
    )
    return list(rows) or ["linkedin"]


async def fetch_all_metrics(z: ZernioClient, platforms: list[str],
                            profile_id: str | None = None) -> dict:
    """Pull analytics for each platform and merge into one combined structure.

    profile_id scopes to one customer (required in white-label mode). Posts are
    tagged with their platform; overview counters are summed. Per-platform
    failures are tracked (not silently swallowed) so a broken fetch doesn't
    look identical to "this account genuinely has zero data"."""
    merged_posts: list[dict] = []
    merged_overview: dict = {}
    failed_platforms: list[str] = []
    for p in platforms:
        try:
            d = await z.get_analytics(platform=p, profile_id=profile_id)
        except ZernioError as e:
            failed_platforms.append(p)
            log.warning("Zernio analytics fetch failed for platform=%s: %s", p, e.message)
            continue
        # Diagnostic only — Zernio's field names for impressions/reach can vary
        # by platform and by personal-vs-organization account type on LinkedIn;
        # this makes the raw shape inspectable without guessing at a fix.
        log.debug("Zernio analytics raw for platform=%s: %s", p, json.dumps(d)[:2000])
        for post in (d.get("posts") or []):
            post.setdefault("platform", p)
            merged_posts.append(post)
        for k, v in (d.get("overview") or {}).items():
            if isinstance(v, (int, float)):
                merged_overview[k] = merged_overview.get(k, 0) + v
    return {"overview": merged_overview, "posts": merged_posts, "failed_platforms": failed_platforms}


@router.get("/zernio")
async def zernio_metrics(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reach & engagement, auto-pulled across ALL the user's connected platforms."""
    key = resolve_zernio_key(current)
    if not key:
        # No raw error — the UI shows a friendly "connect an account" empty state.
        return {"ok": False, "needs_connection": True}
    # White-label: scope to this customer's profile, fail-closed (no profile → nothing).
    profile_id = await ensure_profile(current, db)
    if is_white_label() and not profile_id:
        return {"ok": False, "needs_connection": True}
    platforms = await connected_platforms(current, db)
    async with ZernioClient(settings.zernio_base_url, key) as z:
        try:
            data = await fetch_all_metrics(z, platforms, profile_id)
        except ZernioError as e:
            return {"ok": False, "error": e.message}
    return {
        "ok": True, "summary": _aggregate(data), "data": data, "platforms": platforms,
        "failed_platforms": data.get("failed_platforms") or [],
    }


_INSIGHTS_STRING_FIELDS = (
    "followers", "impressions", "profile_views", "post_count",
    "avg_likes", "avg_comments", "avg_shares",
)


@router.post("/insights")
async def insights(
    body: InsightsRequest, current: User = Depends(get_current_user)
) -> dict:
    """Interpret account metrics via the Hub's analytics model.

    The Hub's linkedin-analytics tool validates these metric fields as
    strings (not numbers), even though they're counts — so stringify before
    sending, or the Hub rejects the call with a 422.
    """
    payload = body.model_dump(exclude_none=True)
    for k in _INSIGHTS_STRING_FIELDS:
        if k in payload:
            payload[k] = str(payload[k])
    data = await _hub_call(current, "analytics", payload)
    return {"ok": True, "data": data}


@router.post("/viral")
async def viral(
    body: ViralRequest, current: User = Depends(get_current_user)
) -> dict:
    """Analyze one post's reach/engagement via the Hub's viral-analyzer."""
    data = await _hub_call(current, "viral_analyzer", body.model_dump(exclude_none=True))
    return {"ok": True, "data": data}
