"""
ZernioClient — async client for the Zernio API (LinkedIn action layer).

Zernio rides LinkedIn's official API. This client covers what Autopilot needs:
  - create / schedule LinkedIn posts
  - list connected accounts and LinkedIn organizations (company pages)
  - read analytics
  - list / reply to company-page comments

Contract (from docs.zernio.com):
  - Base URL: https://zernio.com/api/v1
  - Auth: `Authorization: Bearer <ZERNIO_API_KEY>`
  - Create post: POST /posts  -> 201 {"post": {...}, "message": "..."}
  - Errors return {"error": "...", "details": {...}} with codes 400/401/403/409/429
  - 409 = content-hash dedup (same content to same account within 24h)
  - Optional `x-request-id` (UUID) header for safe-retry idempotency

Usage:
    async with ZernioClient(base_url, api_key) as z:
        post = await z.publish_linkedin_now(account_id="...", content="Hello!")
        # or schedule:
        post = await z.schedule_linkedin(account_id="...", content="...",
                                         scheduled_for="2026-06-10T09:00:00Z")
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger("zernio_client")


# --- Exceptions --------------------------------------------------------------
class ZernioError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None,
                 details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ZernioAuthError(ZernioError):
    """401 — missing or invalid API key."""


class ZernioValidationError(ZernioError):
    """400 — bad request (e.g. empty platforms)."""


class ZernioPermissionError(ZernioError):
    """403 — not allowed (scope/admin)."""


class ZernioDuplicateError(ZernioError):
    """409 — content-hash dedup: same content to same account within 24h."""


class ZernioRateLimitError(ZernioError):
    """429 — rate limited."""


class ZernioServerError(ZernioError):
    """5xx — upstream error."""


class ZernioResponseError(ZernioError):
    """Malformed / unexpected response."""


# --- Client ------------------------------------------------------------------
class ZernioClient:
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
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> "ZernioClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    # -- core request --------------------------------------------------------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["x-request-id"] = idempotency_key

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.request(
                    method, path, json=json, params=params, headers=headers
                )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries:
                    await self._sleep(attempt)
                    continue
                raise ZernioServerError(f"Network error calling {path}: {exc}") from exc

            # Retry transient failures only (never retry 409 — it's a real dup).
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < self.max_retries:
                    await self._sleep(attempt, resp.headers.get("Retry-After"))
                    continue
                self._raise_for_status(resp)

            return self._handle_response(resp, path)

        raise ZernioServerError(f"Failed calling {path} after {self.max_retries} attempts")

    def _handle_response(self, resp: httpx.Response, path: str) -> dict[str, Any]:
        if resp.status_code >= 400:
            self._raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return {}
        try:
            body = resp.json()
        except ValueError as exc:
            raise ZernioResponseError(
                f"Non-JSON response from {path} (status {resp.status_code})",
                status_code=resp.status_code,
            ) from exc
        return body if isinstance(body, dict) else {"data": body}

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        detail, details = ZernioClient._detail(resp)
        code = resp.status_code
        mapping = {
            400: ZernioValidationError,
            401: ZernioAuthError,
            403: ZernioPermissionError,
            409: ZernioDuplicateError,
            429: ZernioRateLimitError,
        }
        if code in mapping:
            raise mapping[code](detail, status_code=code, details=details)
        if code >= 500:
            raise ZernioServerError(detail, status_code=code, details=details)
        raise ZernioError(detail, status_code=code, details=details)

    @staticmethod
    def _detail(resp: httpx.Response) -> tuple[str, dict[str, Any]]:
        try:
            body = resp.json()
            if isinstance(body, dict):
                msg = body.get("error") or body.get("message") or body.get("detail")
                return (str(msg) if msg else f"HTTP {resp.status_code}",
                        body.get("details") or {})
        except ValueError:
            pass
        return (resp.text or f"HTTP {resp.status_code}", {})

    async def _sleep(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = self.backoff_base * (2 ** (attempt - 1))
        else:
            delay = self.backoff_base * (2 ** (attempt - 1))
        logger.debug("Retrying Zernio call in %.2fs (attempt %d)", delay, attempt)
        await asyncio.sleep(delay)

    # -- posts ---------------------------------------------------------------
    async def create_post(
        self,
        *,
        platforms: list[dict[str, Any]],
        content: str | None = None,
        media_items: list[dict[str, Any]] | None = None,
        publish_now: bool = False,
        scheduled_for: str | None = None,
        timezone: str = "UTC",
        hashtags: list[str] | None = None,
        is_draft: bool = False,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """POST /posts. Returns the created post dict (response['post'])."""
        payload: dict[str, Any] = {"platforms": platforms, "timezone": timezone}
        if content is not None:
            payload["content"] = content
        if media_items:
            payload["mediaItems"] = media_items
        if publish_now:
            payload["publishNow"] = True
        if scheduled_for:
            payload["scheduledFor"] = scheduled_for
        if is_draft:
            payload["isDraft"] = True
        if hashtags:
            payload["hashtags"] = hashtags
        payload.update(extra)

        body = await self._request(
            "POST", "/posts", json=payload,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        return body.get("post", body)

    @staticmethod
    def _linkedin_platform(
        account_id: str,
        *,
        organization_urn: str | None = None,
        first_comment: str | None = None,
        document_title: str | None = None,
        disable_link_preview: bool | None = None,
    ) -> dict[str, Any]:
        psd: dict[str, Any] = {}
        if organization_urn:
            psd["organizationUrn"] = organization_urn
        if first_comment:
            psd["firstComment"] = first_comment
        if document_title:
            psd["documentTitle"] = document_title
        if disable_link_preview is not None:
            psd["disableLinkPreview"] = disable_link_preview
        entry: dict[str, Any] = {"platform": "linkedin", "accountId": account_id}
        if psd:
            entry["platformSpecificData"] = psd
        return entry

    async def publish_linkedin_now(
        self,
        *,
        account_id: str,
        content: str,
        media_items: list[dict[str, Any]] | None = None,
        first_comment: str | None = None,
        organization_urn: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Publish to a LinkedIn account immediately (compliant, auto)."""
        return await self.create_post(
            platforms=[self._linkedin_platform(
                account_id, organization_urn=organization_urn,
                first_comment=first_comment)],
            content=content, media_items=media_items, publish_now=True,
            idempotency_key=idempotency_key,
        )

    async def schedule_linkedin(
        self,
        *,
        account_id: str,
        content: str,
        scheduled_for: str,
        timezone: str = "UTC",
        media_items: list[dict[str, Any]] | None = None,
        first_comment: str | None = None,
        organization_urn: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Schedule a LinkedIn post for a future time (compliant, auto)."""
        return await self.create_post(
            platforms=[self._linkedin_platform(
                account_id, organization_urn=organization_urn,
                first_comment=first_comment)],
            content=content, media_items=media_items,
            scheduled_for=scheduled_for, timezone=timezone,
            idempotency_key=idempotency_key,
        )

    # -- accounts / orgs / analytics / comments ------------------------------
    async def list_accounts(self) -> dict[str, Any]:
        """GET /accounts — connected social accounts."""
        return await self._request("GET", "/accounts")

    async def get_linkedin_organizations(self, account_id: str) -> dict[str, Any]:
        """GET /accounts/{id}/linkedin-organizations — company pages."""
        return await self._request(
            "GET", f"/accounts/{account_id}/linkedin-organizations"
        )

    async def get_analytics(
        self, *, platform: str = "linkedin",
        from_date: str | None = None, to_date: str | None = None,
    ) -> dict[str, Any]:
        """GET /analytics — post metrics for a platform/date range."""
        params: dict[str, Any] = {"platform": platform}
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        return await self._request("GET", "/analytics", params=params)

    async def list_comments(self, **params: Any) -> dict[str, Any]:
        """GET /comments — inbox comments (LinkedIn: org pages only)."""
        return await self._request("GET", "/comments", params=params)

    async def reply_comment(self, comment_id: str, message: str) -> dict[str, Any]:
        """Reply to a comment (LinkedIn: org pages only)."""
        return await self._request(
            "POST", f"/comments/{comment_id}/reply", json={"message": message}
        )


__all__ = [
    "ZernioClient",
    "ZernioError",
    "ZernioAuthError",
    "ZernioValidationError",
    "ZernioPermissionError",
    "ZernioDuplicateError",
    "ZernioRateLimitError",
    "ZernioServerError",
    "ZernioResponseError",
]
