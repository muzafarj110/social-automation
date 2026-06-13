"""
Map Hub client errors to clean, user-facing HTTP errors.

The Hub (and the model providers behind it) return raw messages that can leak
internal details — provider org ids, model names, billing URLs, token counts.
Never surface those. Show a friendly message and log the detail server-side.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.clients.hub_client import (
    HubAuthError,
    HubError,
    HubPermissionError,
    HubRateLimitError,
    HubValidationError,
)

log = logging.getLogger("uvicorn.error")


def hub_http(e: HubError) -> HTTPException:
    """A safe HTTPException for any Hub error (raw detail stays in the logs)."""
    log.warning("Hub error (%s): %s", type(e).__name__, getattr(e, "message", e))
    if isinstance(e, HubRateLimitError):
        return HTTPException(429, "The AI service is busy right now. Please try again in a few minutes.")
    if isinstance(e, HubAuthError):
        return HTTPException(401, "Couldn't reach the AI service — check your Hub API key under Accounts.")
    if isinstance(e, HubPermissionError):
        return HTTPException(403, "This AI capability isn't available on your current plan.")
    if isinstance(e, HubValidationError):
        return HTTPException(400, "We couldn't process that request — please adjust your input and try again.")
    return HTTPException(502, "The AI service is temporarily unavailable. Please try again shortly.")
