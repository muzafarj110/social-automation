"""
Publisher service — turns a Post row into a real LinkedIn action via Zernio.

Zernio is app-level: one ZERNIO_API_KEY for the whole SaaS, with each user's
LinkedIn surfaced as a different accountId (LinkedInAccount.zernio_account_id).

Scheduling uses Zernio's native `scheduledFor`, so Zernio owns post timing —
no separate scheduler process needed for publishing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.clients.zernio_client import (
    ZernioClient,
    ZernioDuplicateError,
    ZernioError,
)
from app.core.config import settings
from app.models import post as post_status
from app.models.post import Post


class PublishError(Exception):
    """Raised when publishing/scheduling cannot proceed (config or upstream)."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _require_zernio_key() -> str:
    key = settings.zernio_api_key
    if not key or key.startswith("paste-"):
        raise PublishError(
            "ZERNIO_API_KEY is not set in .env — cannot publish.", status_code=503
        )
    return key


def _client() -> ZernioClient:
    return ZernioClient(settings.zernio_base_url, _require_zernio_key())


def _extract_url(zernio_post: dict[str, Any]) -> str | None:
    platforms = zernio_post.get("platforms") or []
    if platforms and isinstance(platforms[0], dict):
        return platforms[0].get("platformPostUrl")
    return zernio_post.get("platformPostUrl")


async def publish_now(post: Post, zernio_account_id: str) -> Post:
    """Publish a post immediately. Mutates and returns the post (caller commits)."""
    _require_zernio_key()
    async with _client() as z:
        try:
            result = await z.publish_linkedin_now(
                account_id=zernio_account_id,
                content=post.body,
                media_items=post.media,
                first_comment=post.first_comment,
                idempotency_key=f"post-{post.id}-publish",
            )
        except ZernioDuplicateError as e:
            post.status = post_status.FAILED
            post.error = f"Duplicate content (already posted within 24h): {e.message}"
            raise PublishError(post.error, status_code=409) from e
        except ZernioError as e:
            post.status = post_status.FAILED
            post.error = e.message
            raise PublishError(e.message, status_code=e.status_code or 502) from e

    post.zernio_post_id = result.get("_id")
    post.platform_post_url = _extract_url(result)
    post.status = post_status.PUBLISHED
    post.error = None
    return post


async def schedule(post: Post, zernio_account_id: str,
                   scheduled_for: datetime, timezone: str = "UTC") -> Post:
    """Schedule a post via Zernio. Mutates and returns the post (caller commits)."""
    _require_zernio_key()
    async with _client() as z:
        try:
            result = await z.schedule_linkedin(
                account_id=zernio_account_id,
                content=post.body,
                scheduled_for=scheduled_for.isoformat(),
                timezone=timezone,
                media_items=post.media,
                first_comment=post.first_comment,
                idempotency_key=f"post-{post.id}-schedule",
            )
        except ZernioDuplicateError as e:
            post.status = post_status.FAILED
            post.error = f"Duplicate content: {e.message}"
            raise PublishError(post.error, status_code=409) from e
        except ZernioError as e:
            post.status = post_status.FAILED
            post.error = e.message
            raise PublishError(e.message, status_code=e.status_code or 502) from e

    post.zernio_post_id = result.get("_id")
    post.status = post_status.SCHEDULED
    post.scheduled_for = scheduled_for
    post.timezone = timezone
    post.error = None
    return post
