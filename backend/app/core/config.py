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

    # Infra
    database_url: str = Field("", alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
