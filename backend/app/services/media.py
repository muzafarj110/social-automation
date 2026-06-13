"""
Media generation hook (AI image/video) — the plug-in point for later.

Today users attach their own image/video to a post (see Posts UI), which is what
lets media-first platforms (Instagram, TikTok, etc.) publish. AI *generation* of
media is not built yet because it needs an image/video model on the AI Models Hub
— the current `infographic` model outputs HTML, not an uploadable image file.

When that Hub model exists, set HUB_IMAGE_MODEL to its endpoint name and the rest
of the app can call generate_image() to auto-attach media to a post (e.g. in the
campaign engine for media-required platforms) instead of leaving them as drafts.
Per the architecture rule, the model lives on the Hub; this is just the caller.
"""

from __future__ import annotations

from typing import Any

# Set to the Hub endpoint name once an image-generation model is built, e.g. "image_generator".
HUB_IMAGE_MODEL: str | None = None


async def generate_image(hub: Any, prompt: str) -> dict | None:
    """Return an uploadable media item {"type","url"} for `prompt`, or None.

    Returns None (no media) until a Hub image model is configured — callers
    should treat None as "no AI media available, keep as draft for the user".
    """
    if not HUB_IMAGE_MODEL:
        return None
    try:
        data = await hub.call(HUB_IMAGE_MODEL, {"prompt": prompt})
    except Exception:
        return None
    url = data.get("url") or data.get("image_url") or data.get("media_url")
    return {"type": "image", "url": url} if url else None
