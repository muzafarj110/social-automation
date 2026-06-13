"""
Central app settings, loaded from environment / .env.

Uses pydantic-settings so values are typed and validated at startup.
Import the singleton: `from app.core.config import settings`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env  (two levels up from this file: app/core/config.py -> backend/)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


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

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

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
    return Settings()


settings = get_settings()
