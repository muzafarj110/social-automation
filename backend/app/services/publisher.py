"""
Publisher service — turns a Post row into a real LinkedIn action via Zernio.

Each user supplies their OWN Zernio key (User.zernio_api_key_enc), so a user can
only publish to LinkedIn accounts under their own Zernio connection — that's the
multi-tenant isolation boundary. The caller resolves the key and passes it in.

Scheduling uses Zernio's native `scheduledFor`, so Zernio owns post timing —
no separate scheduler process needed for publishing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.clients.zernio_client import (
    ZernioClient,
    ZernioDuplicateError,
    ZernioError,
)
from app.core import platforms as plat
from app.core.config import settings
from app.models import post as post_status
from app.models.post import Post


class SocialProvider(Protocol):
    """The posting backend contract. Today this is Zernio; to swap providers,
    implement these async methods on a new class and return it from
    `make_provider()` — nothing else in the app needs to change.

    Used as an async context manager. Methods may raise ZernioError-style
    exceptions (with `.message` / `.status_code`) that the publisher maps.
    """

    async def __aenter__(self) -> "SocialProvider": ...
    async def __aexit__(self, *exc: Any) -> None: ...

    async def publish_now(self, *, platform: str, account_id: str, content: str,
                          media_items: Any, platform_specific_data: Any,
                          idempotency_key: str) -> dict[str, Any]: ...

    async def schedule(self, *, platform: str, account_id: str, content: str,
                       scheduled_for: str, timezone: str, media_items: Any,
                       platform_specific_data: Any, idempotency_key: str) -> dict[str, Any]: ...

    async def get_post(self, post_id: str) -> dict[str, Any]: ...


class PublishError(Exception):
    """Raised when publishing/scheduling cannot proceed (config or upstream)."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _client(zernio_key: str) -> ZernioClient:
    if not zernio_key:
        raise PublishError(
            "Connect your channels first.",
            status_code=400,
        )
    return ZernioClient(settings.zernio_base_url, zernio_key)


def make_provider(key: str) -> SocialProvider:
    """The single swap point for the posting backend.

    Returns the configured provider (currently Zernio, which already satisfies
    the SocialProvider protocol). To migrate to another provider, implement the
    protocol and switch the return here — callers below stay unchanged. This is
    the abstraction that keeps the app from being locked to one vendor.
    """
    return _client(key)


def _extract_url(zernio_post: dict[str, Any]) -> str | None:
    platforms = zernio_post.get("platforms") or []
    if platforms and isinstance(platforms[0], dict):
        return platforms[0].get("platformPostUrl")
    return zernio_post.get("platformPostUrl")


def _compose_content(post: Post, platform: str) -> str:
    """Body text sent to the platform, adapted to platform norms.

    Hashtags live in their own column for editing/analytics. On platforms that
    support them, any not already in the body are appended; on platforms that
    don't (e.g. Reddit, WhatsApp), they're dropped. The result is trimmed to the
    platform's character limit so a long LinkedIn post doesn't break a tweet.
    """
    body = post.body or ""
    tags = post.hashtags or []
    if tags and plat.supports_hashtags(platform):
        existing = body.lower()
        missing = [
            (t if t.startswith("#") else f"#{t}")
            for t in tags
            if (t if t.startswith("#") else f"#{t}").lower() not in existing
        ]
        if missing:
            sep = "\n\n" if body.strip() else ""
            body = f"{body}{sep}{' '.join(missing)}"

    limit = plat.char_limit(platform)
    if len(body) > limit:
        body = body[: max(0, limit - 1)].rstrip() + "…"  # ellipsis
    return body


def _psd_for(post: Post, platform: str) -> dict | None:
    """Platform-specific data. LinkedIn supports a first-comment; others don't."""
    if platform == "linkedin" and post.first_comment:
        return {"firstComment": post.first_comment}
    return None


def needs_media(post: Post, platform: str) -> bool:
    """True if the platform requires media but the post has none.

    Instagram, TikTok, YouTube, Pinterest and Snapchat reject text-only posts,
    so we block publishing rather than send something Zernio will fail."""
    return plat.meta(platform)["media_required"] and not post.media


def _guard_media(post: Post, platform: str) -> None:
    if needs_media(post, platform):
        post.status = post_status.FAILED
        post.error = (f"{plat.label(platform)} requires an image or video. "
                      f"Add media to this post before publishing.")
        raise PublishError(post.error, status_code=400)


async def publish_now(
    post: Post, zernio_account_id: str, *, platform: str = "linkedin", zernio_key: str
) -> Post:
    """Publish a post immediately. Mutates and returns the post (caller commits)."""
    _guard_media(post, platform)
    async with make_provider(zernio_key) as z:
        try:
            result = await z.publish_now(
                platform=platform,
                account_id=zernio_account_id,
                content=_compose_content(post, platform),
                media_items=post.media,
                platform_specific_data=_psd_for(post, platform),
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
                   scheduled_for: datetime, timezone: str = "UTC",
                   *, platform: str = "linkedin", zernio_key: str) -> Post:
    """Schedule a post via Zernio. Mutates and returns the post (caller commits)."""
    _guard_media(post, platform)
    async with make_provider(zernio_key) as z:
        try:
            result = await z.schedule(
                platform=platform,
                account_id=zernio_account_id,
                content=_compose_content(post, platform),
                scheduled_for=scheduled_for.isoformat(),
                timezone=timezone,
                media_items=post.media,
                platform_specific_data=_psd_for(post, platform),
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


# Zernio status strings mapped to ours (Zernio owns the publish clock).
_PUBLISHED_STATES = {"published", "posted", "completed", "complete", "sent", "success", "live"}
_FAILED_STATES = {"failed", "error", "errored", "rejected", "cancelled", "canceled"}


def _platform_state(zp: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Return (status, url, error) from the first platform entry, if present."""
    platforms = zp.get("platforms") or []
    if platforms and isinstance(platforms[0], dict):
        p0 = platforms[0]
        st = (p0.get("status") or p0.get("state") or "")
        return (st.lower() or None,
                p0.get("platformPostUrl") or p0.get("postUrl"),
                p0.get("error") or p0.get("failureReason"))
    return (None, None, None)


async def sync_status(post: Post, zernio_key: str) -> Post:
    """Poll Zernio for a scheduled post's real state and reconcile ours.

    Best-effort and non-fatal: on any Zernio error we leave the post unchanged
    so listing never breaks. Mutates and returns the post (caller commits).
    """
    if not post.zernio_post_id or not zernio_key:
        return post
    async with make_provider(zernio_key) as z:
        try:
            zp = await z.get_post(post.zernio_post_id)
        except ZernioError:
            return post

    pstat, purl, perr = _platform_state(zp)
    status = pstat or (zp.get("status") or zp.get("state") or "").lower()
    url = purl or _extract_url(zp)

    if status in _PUBLISHED_STATES:
        post.status = post_status.PUBLISHED
        if url:
            post.platform_post_url = url
        post.error = None
    elif status in _FAILED_STATES:
        post.status = post_status.FAILED
        post.error = (perr or zp.get("failureReason") or zp.get("error")
                      or "Publishing failed on Zernio.")
    return post
