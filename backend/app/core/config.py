"""
Central app settings, loaded from environment / .env.

Uses pydantic-settings so values are typed and validated at startup.
Import the singleton: `from app.core.config import settings`.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# backend/.env  (two levels up from this file: app/core/config.py -> backend/)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

# Any of these being present means we're deployed on Railway, not a laptop.
_RAILWAY_ENV_MARKERS = (
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_PROJECT_ID",
    "RAILWAY_STATIC_URL",
    "RAILWAY_SERVICE_ID",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI Models Hub
    # Default to the known Hub URL so a missing env var never crashes boot.
    hub_base_url: str = Field(
        "https://ai-marketing-hub-production-fccb.up.railway.app", alias="HUB_BASE_URL"
    )
    hub_api_key: str = Field("", alias="HUB_API_KEY")

    # Zernio
    zernio_base_url: str = Field("https://zernio.com/api/v1", alias="ZERNIO_BASE_URL")
    zernio_api_key: str = Field("", alias="ZERNIO_API_KEY")

    # Auth
    jwt_secret: str = Field("change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # this email is treated as the admin (full access + admin dashboard)
    admin_email: str = Field("muzafarj110@gmail.com", alias="ADMIN_EMAIL")

    # Infra
    database_url: str = Field("", alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Billing (usage-based credits via Stripe). All optional — billing is simply
    # disabled until STRIPE_SECRET_KEY is set, so the app runs without it.
    stripe_secret_key: str = Field("", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field("", alias="STRIPE_WEBHOOK_SECRET")
    # Credit packs as "price_id:credits,price_id:credits" (Stripe Price IDs).
    # e.g. "price_abc:100,price_def:500". Prices live in Stripe, not here.
    stripe_credit_packs: str = Field("", alias="STRIPE_CREDIT_PACKS")
    # Where Stripe sends the user back after checkout.
    billing_success_url: str = Field("", alias="BILLING_SUCCESS_URL")
    billing_cancel_url: str = Field("", alias="BILLING_CANCEL_URL")
    # Credits granted to every new account so they can try the product.
    free_credits: int = Field(50, alias="FREE_CREDITS")
    # Free trial: this many credits per day for this many days, then must subscribe.
    free_daily_limit: int = Field(5, alias="FREE_DAILY_LIMIT")
    free_trial_days: int = Field(14, alias="FREE_TRIAL_DAYS")
    # Subscription plans as "price_id:tier:credits" (RECURRING Stripe Prices).
    # e.g. "price_a:starter:100,price_b:growth:400,price_c:pro:1200".
    # Each cycle the user's credits reset to their tier's monthly allowance.
    stripe_plans: str = Field("", alias="STRIPE_PLANS")

    # Email via Mailjet HTTP API. Set MAILJET_API_KEY + MAILJET_SECRET_KEY in
    # Railway. Sender is a single verified address (no domain needed) — once
    # aitool4all@gmail.com is verified in Mailjet, it can send to any recipient.
    mailjet_api_key: str = Field("", alias="MAILJET_API_KEY")
    mailjet_secret_key: str = Field("", alias="MAILJET_SECRET_KEY")
    mailjet_from: str = Field("aitool4all@gmail.com", alias="MAILJET_FROM")
    app_base_url: str = Field("", alias="APP_BASE_URL")

    # Where user-uploaded media files (images/videos) are stored. Defaults to
    # a local relative dir so dev "just works"; Railway sets UPLOAD_DIR=/app/uploads.
    upload_dir: str = Field("./uploads", alias="UPLOAD_DIR")

    # Video agent (Faceless Video Pipeline). Script generation calls Claude
    # directly — see app/vendor/faceless_pipeline/steps/generate_script.py.
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    pexels_api_key: str = Field("", alias="PEXELS_API_KEY")

    @property
    def email_enabled(self) -> bool:
        return bool(self.mailjet_api_key and self.mailjet_secret_key)

    @property
    def video_agent_enabled(self) -> bool:
        return bool(self.anthropic_api_key and self.pexels_api_key)

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def subscriptions_enabled(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_plans.strip())

    def plans(self) -> dict[str, dict]:
        """Parse STRIPE_PLANS into {price_id: {"tier": str, "credits": int}}."""
        out: dict[str, dict] = {}
        for part in self.stripe_plans.split(","):
            part = part.strip()
            bits = [b.strip() for b in part.split(":")]
            if len(bits) == 3 and bits[0]:
                try:
                    out[bits[0]] = {"tier": bits[1], "credits": int(bits[2])}
                except ValueError:
                    pass
        return out

    def credit_packs(self) -> dict[str, int]:
        """Parse STRIPE_CREDIT_PACKS into {price_id: credits}."""
        out: dict[str, int] = {}
        for part in self.stripe_credit_packs.split(","):
            part = part.strip()
            if ":" in part:
                pid, _, amt = part.partition(":")
                try:
                    out[pid.strip()] = int(amt)
                except ValueError:
                    pass
        return out


@lru_cache
def get_settings() -> Settings:
    instance = Settings()
    weak_secret = not instance.jwt_secret or instance.jwt_secret == "change-me"
    on_railway = any(os.environ.get(var) for var in _RAILWAY_ENV_MARKERS)
    if weak_secret and on_railway:
        raise RuntimeError(
            "JWT_SECRET is unset or still the default 'change-me'. This secret also "
            "derives the encryption key for stored Zernio/Hub API keys, so leaving it "
            "unset lets anyone forge admin JWTs and decrypt every user's secrets. "
            "Set a strong JWT_SECRET in Railway's project variables before deploying."
        )
    elif weak_secret:
        logger.warning(
            "JWT_SECRET is unset or the default 'change-me'; fine for local dev, "
            "but never deploy like this."
        )
    return instance


# ── Feature Permissions by Profile Type ──────────────────────────────────────
# Maps profile_type → list of available features. Used by @require_feature decorator.
FEATURE_PERMISSIONS: dict[str, set[str]] = {
    # Individual & Influencer: personal growth tools
    "individual": {
        "profile_optimizer",
        "growth_analytics",
        "content_studio",
        "video_studio",
        "video_tools",
        "generate",
        "qa",
        "strategy",
        "autopilot",
        "inbox",
        "profile_studio",
        "analytics",
        "infographics",
        "learn_from_analytics",
        "multi_account",
    },
    "influencer": {
        "profile_optimizer",
        "growth_analytics",
        "content_studio",
        "video_studio",
        "video_tools",
        "generate",
        "qa",
        "strategy",
        "autopilot",
        "inbox",
        "profile_studio",
        "analytics",
        "infographics",
        "learn_from_analytics",
        "multi_account",
    },
    # Startup, Company, Agency: business tools (lead gen, WhatsApp agent)
    "startup": {
        "lead_gen",
        "whatsapp_agent",
        "content_studio",
        "video_studio",
        "video_tools",
        "generate",
        "qa",
        "strategy",
        "autopilot",
        "inbox",
        "profile_studio",
        "infographics",
    },
    "company": {
        "lead_gen",
        "whatsapp_agent",
        "growth_analytics",
        "content_studio",
        "video_studio",
        "video_tools",
        "generate",
        "qa",
        "strategy",
        "autopilot",
        "inbox",
        "profile_studio",
        "analytics",
        "infographics",
        "learn_from_analytics",
        "multi_account",
    },
    "agency": {
        "lead_gen",
        "whatsapp_agent",
        "content_studio",
        "video_studio",
        "video_tools",
        "generate",
        "qa",
        "strategy",
        "autopilot",
        "inbox",
        "profile_studio",
        "infographics",
    },
}


settings = get_settings()
