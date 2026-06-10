"""
Create database tables. Run once for local dev (the app also does this on
startup). For production, prefer Alembic migrations.

Usage (from backend/):  python3 scripts/init_db.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import DATABASE_URL, init_db  # noqa: E402


async def main() -> None:
    await init_db()
    print(f"Tables created on: {DATABASE_URL}")


if __name__ == "__main__":
    asyncio.run(main())
