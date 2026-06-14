"""
Authenticated content generation — uses the logged-in user's own Hub key
(falls back to the .env key in dev if the user hasn't set one yet).
"""

from __future__ import annotations

import asyncio
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.hub_client import HubClient, HubError
from app.core import credits, ttl_cache
from app.core.config import settings
from app.core.hub_errors import hub_http
from app.core.security import decrypt_secret
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/content", tags=["content"])


def _map_hub_error(e: HubError) -> HTTPException:
    return hub_http(e)


def _resolve_hub_key(user: User) -> str:
    if user.hub_api_key_enc:
        key = decrypt_secret(user.hub_api_key_enc)
        if key:
            return key
    # Dev fallback so the endpoint works before per-user keys are set.
    if settings.hub_api_key and not settings.hub_api_key.startswith("paste-"):
        return settings.hub_api_key
    raise HTTPException(400, "AI is temporarily unavailable. Please try again.")


class GeneratePostRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    post_type: str = "Personal Story + Lesson"
    audience: str = "early-stage founders"
    tone: str = "professional but human"
    include_cta: str | None = "question to comments"


@router.post("/generate/post")
async def generate_post(
    req: GeneratePostRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    # Usage-based billing: must have a credit before generating (admins exempt).
    if not credits.has_credits(current, credits.COST_GENERATE):
        raise HTTPException(402, "You're out of credits. Top up under Billing to keep creating.")
    key = _resolve_hub_key(current)
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.generate_text_post(
                topic=req.topic,
                post_type=req.post_type,
                audience=req.audience,
                tone=req.tone,
                include_cta=req.include_cta,
            )
        except HubError as e:
            raise hub_http(e) from e
    # Only charge on success.
    await credits.charge(db, current, credits.COST_GENERATE)
    return {"ok": True, "data": data, "credits": current.credits}


# --- Quality assurance on a piece of content --------------------------------
class QaRequest(BaseModel):
    content: str = Field(..., min_length=1)
    topic: str | None = None
    audience: str = "professionals"
    platform: str = "linkedin"


class OptimizeRequest(BaseModel):
    content: str = Field(..., min_length=1)
    goal: str = "engagement"
    tone: str = "professional"


class InfographicRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    content_points: str = Field(..., min_length=1)
    infographic_type: str = "Timeline / Evolution"
    color_scheme: str = "professional"
    brand_name: str | None = None


@router.post("/qa")
async def qa_check(
    req: QaRequest, current: User = Depends(get_current_user)
) -> dict[str, object]:
    """Run a quality pass on content: numeric score, QA review, AI-detection.

    Three Hub models in parallel so the UI can show we vet content, not blind-post.
    """
    key = _resolve_hub_key(current)
    async with HubClient(settings.hub_base_url, key) as hub:
        async def _safe(name: str, payload: dict):
            try:
                return await hub.call(name, payload)
            except HubError:
                return None

        score, review, ai = await asyncio.gather(
            _safe("score_checker", {"content": req.content, "topic": req.topic or "",
                                    "platform": req.platform}),
            _safe("qa", {"content": req.content, "content_type": "linkedin post",
                         "audience": req.audience}),
            _safe("ai_detector", {"content": req.content, "content_type": "linkedin post"}),
        )
    if score is None and review is None and ai is None:
        raise HTTPException(502, "Quality check failed — the AI service didn't respond.")
    return {"ok": True, "score": score, "qa": review, "ai_detection": ai}


@router.post("/optimize")
async def optimize(
    req: OptimizeRequest, current: User = Depends(get_current_user)
) -> dict[str, object]:
    """Rewrite content to improve it (Hub content-optimizer)."""
    key = _resolve_hub_key(current)
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.call("content_optimizer", req.model_dump())
        except HubError as e:
            raise _map_hub_error(e) from e
    return {"ok": True, "data": data}


@router.post("/infographic")
async def infographic(
    req: InfographicRequest, current: User = Depends(get_current_user)
) -> dict[str, object]:
    """Generate an infographic concept from content points (Hub infographic)."""
    key = _resolve_hub_key(current)
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.call("infographic", req.model_dump(exclude_none=True))
        except HubError as e:
            raise _map_hub_error(e) from e
    return {"ok": True, "data": data}


@router.get("/usage")
async def usage(current: User = Depends(get_current_user)) -> dict[str, object]:
    """The user's Hub plan + consumption — only when they use their OWN key.

    SECURITY: when a user has no personal Hub key, generation falls back to the
    shared/managed server key. We must NOT call the Hub's /api/me in that case,
    because it would return the shared key owner's account (email, plan, referral
    code, usage) to every user. Instead we return a generic "managed" payload.

    For users with their own key, results are cached per-key for 60s (cache key
    is a hash of the API key, so users never see each other's usage).
    """
    own_key = None
    if current.hub_api_key_enc:
        own_key = decrypt_secret(current.hub_api_key_enc)

    if not own_key:
        # Shared/managed capacity — never expose the owner's Hub account.
        return {
            "ok": True,
            "managed": True,
            "data": {"managed": True, "plan": current.plan},
        }

    cache_key = "usage:" + hashlib.sha256(own_key.encode()).hexdigest()
    cached = ttl_cache.get(cache_key)
    if cached is not None:
        return {"ok": True, "data": cached, "cached": True}
    async with HubClient(settings.hub_base_url, own_key) as hub:
        try:
            data = await hub.get_raw("/api/me")
        except HubError as e:
            raise _map_hub_error(e) from e
    ttl_cache.set(cache_key, data, 60)
    return {"ok": True, "data": data}
