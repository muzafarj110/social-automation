"""
Email via Gmail SMTP (or any SMTP provider).
Set SMTP_USER + SMTP_PASS in Railway to enable.
Falls back to Resend if SMTP is not configured and RESEND_API_KEY is set.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.core.config import settings

log = logging.getLogger("uvicorn.error")


def _smtp_send_sync(*, to: str, subject: str, html: str) -> None:
    """Blocking SMTP send — called via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or f"Autopilot <{settings.smtp_user}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.login(settings.smtp_user, settings.smtp_pass)
        s.sendmail(msg["From"], [to], msg.as_string())


async def _smtp_send(*, to: str, subject: str, html: str) -> bool:
    try:
        await asyncio.to_thread(_smtp_send_sync, to=to, subject=subject, html=html)
        log.info("SMTP sent to %s", to)
        return True
    except smtplib.SMTPAuthenticationError as e:
        log.error("SMTP auth failed (check SMTP_PASS): %s", e)
        return False
    except Exception as e:
        log.error("SMTP send error to %s: %s", to, e)
        return False


async def _resend_send(*, to: str, subject: str, html: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.resend_from, "to": [to], "subject": subject, "html": html},
            )
        if r.status_code >= 400:
            log.error("Resend error (%s): %s", r.status_code, r.text[:300])
            return False
        log.info("Resend sent to %s", to)
        return True
    except Exception as e:
        log.error("Resend connection error: %s", e)
        return False


async def send_email(*, to: str, subject: str, html: str) -> bool:
    """Send via SMTP first (more reliable). Falls back to Resend if SMTP not configured."""
    if settings.smtp_enabled:
        return await _smtp_send(to=to, subject=subject, html=html)
    if settings.resend_enabled:
        return await _resend_send(to=to, subject=subject, html=html)
    log.warning("Email disabled — set SMTP_USER+SMTP_PASS or RESEND_API_KEY in Railway")
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
