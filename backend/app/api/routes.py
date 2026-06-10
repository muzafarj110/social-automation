"""
Phase 0 API routes: health, integration status, and a working demo that
generates a LinkedIn post via the (confirmed-live) Hub.

These demo routes use the Hub key from .env. In the real SaaS, each user's
key comes from their account record — that swap happens when auth lands.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.clients.hub_client import (
    HubAuthError,
    HubClient,
    HubError,
    HubPermissionError,
    HubRateLimitError,
)
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status", tags=["system"])
async def status() -> dict[str, object]:
    """Report which integrations are configured (never returns secrets)."""
    def configured(v: str) -> bool:
        return bool(v) and not v.startswith("paste-") and v != "change-me"

    return {
        "hub": {
            "base_url": settings.hub_base_url,
            "configured": configured(settings.hub_api_key),
        },
        "zernio": {
            "base_url": settings.zernio_base_url,
            "configured": configured(settings.zernio_api_key),
        },
    }


class GeneratePostRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    post_type: str = "Personal Story + Lesson"
    audience: str = "early-stage founders"
    tone: str = "professional but human"
    include_cta: str | None = "question to comments"


@router.post("/generate/post", tags=["content"])
async def generate_post(req: GeneratePostRequest) -> dict[str, object]:
    """Generate a LinkedIn post through the AI Models Hub."""
    if not settings.hub_api_key or settings.hub_api_key.startswith("paste-"):
        raise HTTPException(503, "HUB_API_KEY is not set in .env")

    async with HubClient(settings.hub_base_url, settings.hub_api_key) as hub:
        try:
            data = await hub.generate_text_post(
                topic=req.topic,
                post_type=req.post_type,
                audience=req.audience,
                tone=req.tone,
                include_cta=req.include_cta,
            )
        except HubRateLimitError as e:
            raise HTTPException(429, e.message) from e
        except HubAuthError as e:
            raise HTTPException(401, e.message) from e
        except HubPermissionError as e:
            raise HTTPException(403, e.message) from e
        except HubError as e:
            raise HTTPException(502, f"Hub error: {e.message}") from e

    return {"ok": True, "data": data}
