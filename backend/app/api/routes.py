"""
Phase 0 API routes: health and integration status.

Note: post generation now lives exclusively behind auth + credit metering in
app/api/content.py (POST /content/generate/post). The old unauthenticated
demo route (POST /generate/post), which called the shared Hub key with no
auth and no rate limiting, has been removed as it allowed unauthenticated
callers to exhaust/rack up cost on the shared paid key.
"""

from __future__ import annotations

from fastapi import APIRouter

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
