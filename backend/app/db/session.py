"""
Async database engine + session.

Local dev defaults to a SQLite file (zero setup). In production set
DATABASE_URL to your Railway Postgres URL and it's normalized to the async
psycopg driver automatically.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base


def _normalize_url(url: str) -> str:
    if not url:
        # Local dev fallback — no Postgres needed.
        return "sqlite+aiosqlite:///./autopilot.db"
    # Railway / Heroku give "postgresql://..."; SQLAlchemy async needs a driver.
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_url(settings.database_url)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, rolls back on error, always closes."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Auto-create tables on the local SQLite dev DB only.

    When DATABASE_URL is set (e.g. Railway Postgres), schema is owned by Alembic
    migrations — run `alembic upgrade head` instead. This avoids create_all and
    migrations fighting over the same schema in production.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    # Import models so they register on Base.metadata.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
