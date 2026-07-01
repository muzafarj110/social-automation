"""
Email sending via SMTP (works with Gmail, Outlook, or any SMTP provider).

Inert until SMTP_USER + SMTP_PASS are both set — send_email() returns False
instead of raising, so the app runs fine without email configured.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

log = logging.getLogger("uvicorn.error")


def _smtp_send(*, to: str, subject: str, html: str) -> None:
    """Blocking SMTP send — run via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or f"Autopilot <{settings.smtp_user}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_pass)
        server.sendmail(settings.smtp_from, [to], msg.as_string())


async def send_email(*, to: str, subject: str, html: str) -> bool:
    """Send one email. Returns True on success, False if disabled or it failed."""
    if not settings.email_enabled:
        log.warning("Email disabled — set SMTP_USER and SMTP_PASS to enable")
        return False
    try:
        await asyncio.to_thread(_smtp_send, to=to, subject=subject, html=html)
        return True
    except Exception as e:
        log.warning("SMTP send error: %s", e)
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
