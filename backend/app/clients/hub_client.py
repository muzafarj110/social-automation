"""
HubClient — async client for the AI Models Hub API.

The Hub is the content brain for LinkedIn Autopilot. Every AI endpoint:
  - is POST, JSON body
  - authenticates with the `X-API-Key` header (each SaaS user has their own key)
  - returns {"success": true, "data": {...}, "log_id": int} on success

This client is per-user: construct one with the user's key (see `from_user`).
It maps HTTP errors to typed exceptions and retries transient failures
(429 / 5xx) with exponential backoff.

Usage:
    async with HubClient(base_url, api_key) as hub:
        result = await hub.generate_text_post(
            topic="...", post_type="Personal Story + Lesson",
            audience="early-stage founders", tone="professional but human",
            include_cta="question to comments",
        )
        print(result["full_post"])
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("hub_client")

# --- Endpoint registry -------------------------------------------------------
# Central map so callers / pipelines can reference endpoints by stable name.
# Paths verified against the live Hub OpenAPI spec (/openapi.json).
ENDPOINTS: dict[str, str] = {
    "text_post": "/api/linkedin-text-post",
    "post_series": "/api/linkedin-post-series",
    "calendar": "/api/linkedin-calendar",               # plans a content calendar
    "comment_writer": "/api/linkedin-comment",          # was -comment-writer (404)
    "dm_writer": "/api/linkedin-dm",                     # was -dm-writer (404)
    "outreach_campaign": "/api/linkedin-outreach-campaign",
    "profile_optimizer": "/api/linkedin-profile",        # was -profile-optimizer (404)
    "headline_variants": "/api/linkedin-headline-variants",
    "featured_section": "/api/linkedin-featured-section",   # profile featured picks
    "recommendation": "/api/linkedin-recommendation",       # draft a recommendation
    "engagement_strategy": "/api/linkedin-engagement-strategy",
    "analytics": "/api/linkedin-analytics",            # interpret account metrics
    "viral_analyzer": "/api/linkedin-viral-analyzer",  # analyze one post's reach
    # Content quality (QA) tools — not LinkedIn-specific
    "qa": "/api/qa",                                   # quality review + criteria
    "score_checker": "/api/score-checker",             # numeric quality score
    "ai_detector": "/api/ai-detector",                 # flags robotic / AI-sounding text
    "content_optimizer": "/api/content-optimizer",     # rewrite to improve
    "infographic": "/api/infographic",                 # infographic from content points
    # Strategy brain (platform-agnostic)
    "brand_voice": "/api/brand-voice",
    "customer_persona": "/api/customer-persona",
    "uvp": "/api/uvp",
    "competitor_analysis": "/api/competitor-analysis",
    "content_strategy": "/api/content-strategy",
    "marketing_report": "/api/marketing-report",
}


# --- Exceptions --------------------------------------------------------------
class HubError(Exception):
    """Base class for all Hub client errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class HubAuthError(HubError):
    """401 — missing or invalid API key."""


class HubValidationError(HubError):
    """400 — bad/empty input (e.g. 'Topic cannot be empty')."""


class HubPermissionError(HubError):
    """403 — model not available on this key's plan / allowed_models."""


class HubRateLimitError(HubError):
    """429 — monthly call limit reached (free = 50/month)."""


class HubServerError(HubError):
    """500 — upstream Hub exception."""


class HubResponseError(HubError):
    """Malformed response or success=false envelope."""


# --- Client ------------------------------------------------------------------
class HubClient:
    """Async client for one user's Hub API key.

    Construct per request/user. Safe to reuse across calls within a request.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise ValueError("api_key is required")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        # Allow dependency injection of a client (used in tests with MockTransport).
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        )

    # -- lifecycle -----------------------------------------------------------
    async def __aenter__(self) -> "HubClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    # -- core call -----------------------------------------------------------
    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to an endpoint, with retries, and return the unwrapped `data` dict."""
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.post(
                    endpoint,
                    json=payload,
                    headers={"X-API-Key": self.api_key},
                )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    await self._sleep(attempt)
                    continue
                raise HubServerError(f"Network error calling {endpoint}: {exc}") from exc

            # Retryable status codes
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < self.max_retries:
                    await self._sleep(attempt, retry_after=resp.headers.get("Retry-After"))
                    continue
                self._raise_for_status(resp)  # exhausted retries -> raise typed error

            # Non-retryable: validate and return (or raise typed error)
            return self._handle_response(resp, endpoint)

        # Should not reach here, but guard anyway.
        raise HubServerError(
            f"Failed calling {endpoint} after {self.max_retries} attempts: {last_exc}"
        )

    def _handle_response(self, resp: httpx.Response, endpoint: str) -> dict[str, Any]:
        if resp.status_code >= 400:
            self._raise_for_status(resp)

        try:
            # strict=False tolerates raw control chars (unescaped newlines/tabs)
            # that the Hub sometimes embeds in string values.
            body = json.loads(resp.text, strict=False)
        except ValueError as exc:
            raise HubResponseError(
                f"Non-JSON response from {endpoint} (status {resp.status_code})",
                status_code=resp.status_code,
            ) from exc

        if not isinstance(body, dict) or not body.get("success"):
            detail = body.get("detail") if isinstance(body, dict) else str(body)
            raise HubResponseError(
                f"Hub returned an unsuccessful envelope from {endpoint}: {detail}",
                status_code=resp.status_code,
            )

        data = body.get("data")
        if not isinstance(data, dict):
            raise HubResponseError(
                f"Missing 'data' object in response from {endpoint}",
                status_code=resp.status_code,
            )
        # Attach log_id for traceability without polluting data semantics.
        data.setdefault("_log_id", body.get("log_id"))
        return data

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        detail = HubClient._detail(resp)
        code = resp.status_code
        if code == 401:
            raise HubAuthError(detail, status_code=401)
        if code == 400:
            raise HubValidationError(detail, status_code=400)
        if code == 403:
            raise HubPermissionError(detail, status_code=403)
        if code == 429:
            raise HubRateLimitError(detail, status_code=429)
        if code >= 500:
            raise HubServerError(detail, status_code=code)
        raise HubError(detail, status_code=code)

    @staticmethod
    def _detail(resp: httpx.Response) -> str:
        try:
            body = json.loads(resp.text, strict=False)
            if isinstance(body, dict) and "detail" in body:
                return str(body["detail"])
        except ValueError:
            pass
        return resp.text or f"HTTP {resp.status_code}"

    async def _sleep(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = self.backoff_base * (2 ** (attempt - 1))
        else:
            delay = self.backoff_base * (2 ** (attempt - 1))
        logger.debug("Retrying Hub call in %.2fs (attempt %d)", delay, attempt)
        await asyncio.sleep(delay)

    # -- raw GET (for usage/status endpoints that aren't the data envelope) --
    async def get_raw(self, path: str) -> dict[str, Any]:
        """GET a Hub path and return its parsed JSON (e.g. /api/me usage)."""
        resp = await self._client.get(path, headers={"X-API-Key": self.api_key})
        if resp.status_code >= 400:
            self._raise_for_status(resp)
        try:
            body = json.loads(resp.text, strict=False)
        except ValueError as exc:
            raise HubResponseError(f"Non-JSON response from {path}") from exc
        return body if isinstance(body, dict) else {"data": body}

    # -- generic passthrough -------------------------------------------------
    async def call(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call any registered endpoint by its short name (see ENDPOINTS)."""
        try:
            endpoint = ENDPOINTS[name]
        except KeyError as exc:
            raise ValueError(
                f"Unknown Hub endpoint '{name}'. Valid: {', '.join(ENDPOINTS)}"
            ) from exc
        return await self._post(endpoint, payload)

    # -- typed convenience methods ------------------------------------------
    # Only text_post has a documented input schema; the rest accept the
    # endpoint's documented params as kwargs and pass through unchanged.

    async def generate_text_post(
        self,
        *,
        topic: str,
        post_type: str,
        audience: str,
        tone: str,
        include_cta: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """POST /api/linkedin-text-post → single LinkedIn post.

        Returns the `data` dict: hook, full_post, character_count, hashtags,
        cta_line, alternative_hooks, alternative_posts, formatting_tips,
        best_time_to_post, why_this_works.
        """
        payload: dict[str, Any] = {
            "topic": topic,
            "post_type": post_type,
            "audience": audience,
            "tone": tone,
        }
        if include_cta is not None:
            payload["include_cta"] = include_cta
        payload.update(extra)
        return await self.call("text_post", payload)

    async def generate_post_series(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-post-series → content calendar / multi-post series."""
        return await self.call("post_series", params)

    async def write_comment(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-comment → comment draft for the approval inbox.

        Params (confirmed via Hub OpenAPI): post_topic (req), your_role (req),
        post_summary, your_goal, tone.
        """
        return await self.call("comment_writer", params)

    async def write_dm(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-dm → DM draft(s) (manual send).

        Params: prospect_name (req), prospect_role (req), your_role (req),
        your_offer, goal, num_messages (int).
        """
        return await self.call("dm_writer", params)

    async def outreach_campaign(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-outreach-campaign → multi-step DM sequence.

        Params: your_role (req), your_offer (req), target_role (req),
        target_industry, campaign_goal, num_touchpoints (int).
        """
        return await self.call("outreach_campaign", params)

    async def optimize_profile(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-profile → profile rewrite suggestions.

        Params: current_headline (req), current_summary (req), role (req),
        industry (req), goals.
        """
        return await self.call("profile_optimizer", params)

    async def headline_variants(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-headline-variants → headline A/B options."""
        return await self.call("headline_variants", params)

    async def engagement_strategy(self, **params: Any) -> dict[str, Any]:
        """POST /api/linkedin-engagement-strategy → strategy + analytics read."""
        return await self.call("engagement_strategy", params)


__all__ = [
    "HubClient",
    "ENDPOINTS",
    "HubError",
    "HubAuthError",
    "HubValidationError",
    "HubPermissionError",
    "HubRateLimitError",
    "HubServerError",
    "HubResponseError",
]
