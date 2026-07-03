"""
Email via Resend HTTP API (https://resend.com).
Set RESEND_API_KEY + RESEND_FROM in Railway.
Note: without a verified domain, Resend only delivers to the account owner's email.
For beta, registration auto-verifies users so they are never blocked by email.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger("uvicorn.error")
_RESEND_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str) -> bool:
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
            log.warning("Resend error (%s) to %s: %s", r.status_code, to, r.text[:300])
            return False
        log.info("Email sent to %s via Resend", to)
        return True
    except Exception as e:
        log.warning("Resend error to %s: %s", to, e)
        return False


def verification_email_html(verify_url: str) -> str:
    return (
        f"<div style='font-family:system-ui,sans-serif;max-width:480px'>"
        f"<h2>Confirm your email</h2>"
        f"<p>Welcome to Autopilot! Click the button below to verify your email address.</p>"
        f"<p><a href='{verify_url}' style='display:inline-block;background:#0d9488;"
        f"color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>"
        f"Verify my email</a></p>"
        f"<p style='color:#666;font-size:13px'>If you didn't create this account, ignore this email.</p></div>"
    )


def reset_email_html(reset_url: str) -> str:
    return (
        f"<div style='font-family:system-ui,sans-serif;max-width:480px'>"
        f"<h2>Reset your password</h2>"
        f"<p>Click the button below to choose a new password. Expires in 1 hour.</p>"
        f"<p><a href='{reset_url}' style='display:inline-block;background:#0d9488;"
        f"color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>"
        f"Reset password</a></p>"
        f"<p style='color:#666;font-size:13px'>If you didn't request this, ignore this email.</p></div>"
    )
