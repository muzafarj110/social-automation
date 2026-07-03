"""
Email via SendGrid HTTP API — https://sendgrid.com
Free: 100 emails/day, no custom domain needed (just verify one sender email).
Railway-compatible (HTTP, not SMTP).
Set SENDGRID_API_KEY + SENDGRID_FROM in Railway to enable.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger("uvicorn.error")
_SG_URL = "https://api.sendgrid.com/v3/mail/send"


async def send_email(*, to: str, subject: str, html: str) -> bool:
    if not settings.email_enabled:
        log.warning("Email disabled — set SENDGRID_API_KEY + SENDGRID_FROM in Railway")
        return False
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                _SG_URL,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": settings.sendgrid_from, "name": "Autopilot"},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html}],
                },
            )
        if r.status_code not in (200, 202):
            log.error("SendGrid error (%s) to %s: %s", r.status_code, to, r.text[:400])
            return False
        log.info("Email sent to %s via SendGrid", to)
        return True
    except Exception as e:
        log.error("SendGrid send error to %s: %s", to, e)
        return False


def verification_email_html(verify_url: str) -> str:
    return (
        f"<div style='font-family:system-ui,sans-serif;max-width:480px'>"
        f"<h2>Confirm your email</h2>"
        f"<p>Welcome to Autopilot! Click the button below to verify your email "
        f"address and activate your account. This link expires in 24 hours.</p>"
        f"<p><a href='{verify_url}' style='display:inline-block;background:#0d9488;"
        f"color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>"
        f"Verify my email</a></p>"
        f"<p style='color:#666;font-size:13px'>If you didn't create this account, "
        f"you can safely ignore this email.</p></div>"
    )


def reset_email_html(reset_url: str) -> str:
    return (
        f"<div style='font-family:system-ui,sans-serif;max-width:480px'>"
        f"<h2>Reset your password</h2>"
        f"<p>We received a request to reset your password. Click the button below "
        f"to choose a new one. This link expires in 1 hour and can be used once.</p>"
        f"<p><a href='{reset_url}' style='display:inline-block;background:#0d9488;"
        f"color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>"
        f"Reset password</a></p>"
        f"<p style='color:#666;font-size:13px'>If you didn't request this, you can "
        f"safely ignore this email.</p></div>"
    )
