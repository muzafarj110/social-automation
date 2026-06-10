"""
Authenticated content generation — uses the logged-in user's own Hub key
(falls back to the .env key in dev if the user hasn't set one yet).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.clients.hub_client import (
    HubAuthError,
    HubClient,
    HubError,
    HubPermissionError,
    HubRateLimitError,
)
from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.user import User

router = APIRouter(prefix="/content", tags=["content"])


def _resolve_hub_key(user: User) -> str:
    if user.hub_api_key_enc:
        key = decrypt_secret(user.hub_api_key_enc)
        if key:
            return key
    # Dev fallback so the endpoint works before per-user keys are set.
    if settings.hub_api_key and not settings.hub_api_key.startswith("paste-"):
        return settings.hub_api_key
    raise HTTPException(400, "No Hub API key on file. Set one via PUT /api/auth/me/hub-key.")


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
) -> dict[str, object]:
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
        except HubRateLimitError as e:
            raise HTTPException(429, e.message) from e
        except HubAuthError as e:
            raise HTTPException(401, e.message) from e
        except HubPermissionError as e:
            raise HTTPException(403, e.message) from e
        except HubError as e:
            raise HTTPException(502, f"Hub error: {e.message}") from e
    return {"ok": True, "data": data}
