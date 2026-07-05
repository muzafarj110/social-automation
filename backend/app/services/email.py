"""
Email via Mailjet HTTP API (https://mailjet.com).
Set MAILJET_API_KEY + MAILJET_SECRET_KEY in Railway.
Sender is a verified single address (no domain needed) — MAILJET_FROM,
defaulting to aitool4all@gmail.com. Once that address is verified in Mailjet
(Account Settings -> Sender addresses), it can send to ANY recipient.

All outgoing templates share one branded, table-based HTML layout (see
`_shell`) so every email — verification, reset, welcome, marketing, support —
looks consistent and renders reliably across email clients. Each template
function returns an (html, text) tuple; the plain-text part meaningfully
improves inbox placement over HTML-only mail.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger("uvicorn.error")
_MAILJET_URL = "https://api.mailjet.com/v3.1/send"

_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
_SUPPORT_EMAIL = "aitool4all@gmail.com"


def unsubscribe_mailto() -> str:
    return f"mailto:{_SUPPORT_EMAIL}?subject=Unsubscribe"


async def send_email(
    *, to: str, subject: str, html: str, text: str | None = None,
    list_unsubscribe: str | None = None,
) -> bool:
    if not settings.email_enabled:
        return False
    try:
        message: dict = {
            "From": {"Email": settings.mailjet_from, "Name": "Autopilot"},
            "To": [{"Email": to}],
            "Subject": subject,
            "HTMLPart": html,
        }
        if text is not None:
            message["TextPart"] = text
        if list_unsubscribe is not None:
            # No real one-click HTTP unsubscribe endpoint exists yet, so this
            # is mailto-only — List-Unsubscribe-Post is deliberately omitted,
            # since that header specifically claims one-click HTTPS support.
            message["Headers"] = {"List-Unsubscribe": f"<{list_unsubscribe}>"}
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                _MAILJET_URL,
                auth=(settings.mailjet_api_key, settings.mailjet_secret_key),
                json={"Messages": [message]},
            )
        if r.status_code >= 400:
            log.warning("Mailjet error (%s) to %s: %s", r.status_code, to, r.text[:300])
            return False
        log.info("Email sent to %s via Mailjet", to)
        return True
    except Exception as e:
        log.warning("Mailjet error to %s: %s", to, e)
        return False


def _shell(preheader: str, content_html: str, unsubscribe: bool = False) -> str:
    footer_extra = (
        "<p style=\"margin:8px 0 0;\">"
        f"<a href=\"{unsubscribe_mailto()}\" style=\"color:#667085;text-decoration:underline;\">Unsubscribe</a> "
        "from marketing emails. Account and billing emails will still be sent.</p>"
        if unsubscribe else ""
    )
    return f"""<span style="display:none;max-height:0;overflow:hidden;">{preheader}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f6f7fb" style="background-color:#f6f7fb;">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="max-width:600px;width:100%;background-color:#ffffff;border:1px solid #eaecf0;border-radius:12px;">
        <tr>
          <td style="padding:32px 32px 20px;">
            <div style="font-family:{_FONT};font-size:20px;font-weight:700;color:#101828;">Autopilot</div>
            <div style="font-family:{_FONT};font-size:11px;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;color:#667085;margin-top:4px;">Your AI Marketing Team</div>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px;font-family:{_FONT};font-size:15px;line-height:1.6;color:#101828;">
            {content_html}
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px;border-top:1px solid #eaecf0;font-family:{_FONT};font-size:12px;line-height:1.6;color:#667085;">
            <p style="margin:0;">Autopilot — Your AI Marketing Team</p>
            <p style="margin:4px 0 0;">Questions? Reply to this email or write to {_SUPPORT_EMAIL}</p>
            {footer_extra}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""


def _text_footer() -> str:
    return "—\nAutopilot — Your AI Marketing Team\nQuestions? aitool4all@gmail.com"


def verification_email_html(verify_url: str) -> tuple[str, str]:
    content_html = f"""<h2 style="margin:0 0 16px;font-size:19px;line-height:1.4;font-weight:700;color:#101828;">Confirm your email address</h2>
<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#101828;">Welcome to Autopilot. We're glad you're here.</p>
<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#101828;">To activate your account and put your AI marketing team to work, please confirm that this is your email address.</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 24px;">
  <tr>
    <td style="border-radius:8px;background-color:#36ADA3;">
      <a href="{verify_url}" target="_blank" style="display:inline-block;background:#36ADA3;color:#ffffff;padding:12px 28px;border-radius:8px;font-weight:600;text-decoration:none;font-size:15px;font-family:{_FONT};">Verify my email</a>
    </td>
  </tr>
</table>
<p style="margin:0 0 8px;font-size:15px;line-height:1.6;color:#101828;">This link expires in 24 hours. If the button above doesn't work, copy and paste this URL into your browser:</p>
<p style="margin:0 0 20px;font-size:14px;line-height:1.6;word-break:break-all;"><a href="{verify_url}" style="color:#2a8c84;text-decoration:underline;">{verify_url}</a></p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#667085;">If you didn't create an Autopilot account, you can safely ignore this email — no further action is needed.</p>"""
    html = _shell("Verify your email to activate your Autopilot account and AI marketing team.", content_html)
    text = f"""Confirm your email address

Welcome to Autopilot. We're glad you're here.

To activate your account and put your AI marketing team to work, please confirm that this is your email address by visiting the link below:

{verify_url}

This link expires in 24 hours.

If you didn't create an Autopilot account, you can safely ignore this email — no further action is needed.

{_text_footer()}"""
    return html, text


def reset_email_html(reset_url: str) -> tuple[str, str]:
    content_html = f"""<h2 style="margin:0 0 16px;font-size:19px;font-weight:700;color:#101828;">Reset your password</h2>
<p style="margin:0 0 16px;">We received a request to reset the password for your Autopilot account. Click the button below to choose a new one.</p>
<p style="margin:0 0 24px;">
  <a href="{reset_url}" style="display:inline-block;background:#36ADA3;color:#ffffff;padding:12px 28px;border-radius:8px;font-weight:600;text-decoration:none;font-size:15px;">Reset password</a>
</p>
<p style="margin:0 0 16px;">For your security, this link will expire in <strong>1 hour</strong>.</p>
<p style="margin:0 0 16px;">If you didn't request a password reset, you can safely ignore this email — your password will remain unchanged.</p>
<p style="margin:0;font-size:13px;color:#667085;">If the button doesn't work, copy and paste this link into your browser:<br><a href="{reset_url}" style="color:#2a8c84;word-break:break-all;">{reset_url}</a></p>"""
    html = _shell("Your password reset link expires in 1 hour.", content_html)
    text = f"""Reset your password

We received a request to reset the password for your Autopilot account.

Reset your password using the link below:
{reset_url}

For your security, this link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email — your password will remain unchanged.

Questions? Reply to this email or write to aitool4all@gmail.com.

Autopilot — Your AI Marketing Team"""
    return html, text


def welcome_email_html(name: str | None, app_url: str) -> tuple[str, str]:
    display_name = name or "there"
    content_html = f"""<h2 style="margin:0 0 16px 0;font-family:{_FONT};font-size:19px;line-height:1.3;font-weight:700;color:#101828;">Welcome aboard, {display_name}.</h2>

<p style="margin:0 0 16px 0;font-family:{_FONT};font-size:15px;line-height:1.6;color:#101828;">Your account is verified, and your AI marketing team is ready to get to work. Autopilot drafts, schedules, and publishes content across LinkedIn, TikTok, Instagram, YouTube, and more — while keeping an eye on your competitors, listening to what's being said about your brand, and handling SEO/GEO in the background.</p>

<p style="margin:0 0 16px 0;font-family:{_FONT};font-size:15px;line-height:1.6;color:#101828;">In short: the work a marketing team would normally spend hours on, handled automatically — so you can focus on running your business.</p>

<p style="margin:0 0 8px 0;font-family:{_FONT};font-size:15px;line-height:1.6;font-weight:600;color:#101828;">A few things worth trying first:</p>
<ul style="margin:0 0 24px 0;padding:0 0 0 20px;font-family:{_FONT};font-size:15px;line-height:1.6;color:#101828;">
  <li style="margin:0 0 8px 0;">Connect a social account to start publishing</li>
  <li style="margin:0 0 8px 0;">Generate your first post with the AI content writer</li>
  <li style="margin:0 0 8px 0;">Add a competitor to track automatically</li>
</ul>

<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 8px 0;">
  <tr>
    <td style="border-radius:8px;" bgcolor="#36ADA3">
      <a href="{app_url}" target="_blank" style="display:inline-block;background:#36ADA3;color:#ffffff;padding:12px 28px;border-radius:8px;font-family:{_FONT};font-weight:600;text-decoration:none;font-size:15px;">Open Autopilot</a>
    </td>
  </tr>
</table>

<p style="margin:24px 0 0 0;font-family:{_FONT};font-size:14px;line-height:1.6;color:#667085;">Questions about getting started? Just reply to this email — we're happy to help.</p>"""
    html = _shell("Your account is verified. Let's get your first post drafted and live.", content_html)
    text = f"""Welcome aboard, {display_name}.

Your account is verified, and your AI marketing team is ready to get to work. Autopilot drafts, schedules, and publishes content across LinkedIn, TikTok, Instagram, YouTube, and more — while keeping an eye on your competitors, listening to what's being said about your brand, and handling SEO/GEO in the background.

In short: the work a marketing team would normally spend hours on, handled automatically, so you can focus on running your business.

A few things worth trying first:
- Connect a social account to start publishing
- Generate your first post with the AI content writer
- Add a competitor to track automatically

Open Autopilot: {app_url}

Questions about getting started? Just reply to this email — we're happy to help.

{_text_footer()}"""
    return html, text


def marketing_email_html(
    headline: str, body_html: str, body_text: str, cta_text: str, cta_url: str
) -> tuple[str, str]:
    content_html = f"""<h2 style="margin:0 0 16px 0;font-size:19px;line-height:1.4;font-weight:700;color:#101828;">{headline}</h2>
{body_html}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0 4px 0;">
  <tr>
    <td align="center" bgcolor="#36ADA3" style="border-radius:8px;">
      <a href="{cta_url}" style="display:inline-block;background-color:#36ADA3;color:#ffffff;padding:12px 28px;border-radius:8px;font-weight:600;text-decoration:none;font-size:15px;font-family:{_FONT};">{cta_text}</a>
    </td>
  </tr>
</table>"""
    html = _shell(f"{headline} — read more inside from your Autopilot team.", content_html, unsubscribe=True)
    text = f"""{headline}

{body_text}

{cta_text}: {cta_url}

{_text_footer()}"""
    return html, text


def support_email_html(name: str, message_preview: str) -> tuple[str, str]:
    content_html = f"""<h2 style="margin:0 0 16px 0;font-size:19px;line-height:1.3;font-weight:700;color:#101828;">We've received your message</h2>
<p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#101828;">Hi {name},</p>
<p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#101828;">Thanks for reaching out to Autopilot support. This email confirms your message has landed safely in our queue, and a real person on our team will personally review it.</p>
<p style="margin:0 0 8px 0;font-size:14px;line-height:1.6;font-weight:600;color:#101828;">What you sent us:</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px 0;background-color:#e6f5f2;border-radius:8px;">
  <tr>
    <td style="padding:16px 20px;font-size:14px;line-height:1.6;color:#101828;font-style:italic;">
      "{message_preview}"
    </td>
  </tr>
</table>
<p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#101828;">We typically respond within one business day. If anything else comes to mind in the meantime, just reply directly to this email — your note will be added to the same thread, so there's no need to submit the form again.</p>
<p style="margin:0;font-size:15px;line-height:1.6;color:#101828;">Thanks for your patience,<br>The Autopilot Team</p>"""
    html = _shell("Thanks for contacting Autopilot. We typically reply within one business day.", content_html)
    text = f"""We've received your message

Hi {name},

Thanks for reaching out to Autopilot support. This email confirms your message has landed safely in our queue, and a real person on our team will personally review it.

What you sent us:
"{message_preview}"

We typically respond within one business day. If anything else comes to mind in the meantime, just reply directly to this email — your note will be added to the same thread, so there's no need to submit the form again.

Thanks for your patience,
The Autopilot Team

{_text_footer()}"""
    return html, text
