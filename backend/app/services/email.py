"""
Email sending via Resend (https://resend.com).

Inert until RESEND_API_KEY is set — send_email() returns False instead of raising,
so the app runs fine without email configured. Used for password-reset links.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger("uvicorn.error")
_RESEND_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str) -> bool:
    """Send one email. Returns True on success, False if disabled or it failed."""
    if not settings.email_enabled:
        return False
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.resend_from, "to": [to], "subject": subject, "html": html},
            )
        if r.status_code >= 400:
            log.warning("Resend send failed (%s): %s", r.status_code, r.text[:300])
            return False
        return True
    except Exception as e:  # never let email break the request flow
        log.warning("Resend send error: %s", e)
        return False


def reset_email_html(reset_url: str) -> str:
    return (
        f"<div style='font-family:system-ui,sans-serif;max-width:480px'>"
        f"<h2>Reset your password</h2>"
        f"<p>We received a request to reset your password. Click the button below "
        f"to choose a new one. This link expires in 1 hour and can be used once.</p>"
        f"<p><a href='{reset_url}' style='display:inline-block;background:#7c5cfc;"
        f"color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>"
        f"Reset password</a></p>"
        f"<p style='color:#666;font-size:13px'>If you didn't request this, you can "
        f"safely ignore this email.</p></div>"
    )
