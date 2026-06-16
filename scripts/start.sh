#!/bin/sh
# Smart startup: handles both fresh databases and legacy databases that were
# created by init_db() / create_all() before Alembic was introduced.
set -e

python3 - <<'PYEOF'
import os, sys

raw_url = os.environ.get("DATABASE_URL", "")

# Normalise URL for synchronous driver (same logic as alembic/env.py)
if raw_url.startswith("postgresql+asyncpg://"):
    url = raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif raw_url.startswith("postgresql://"):
    url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif raw_url.startswith("postgres://"):
    url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
elif raw_url.startswith("sqlite+aiosqlite://"):
    url = raw_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
elif raw_url:
    url = raw_url
else:
    url = "sqlite:///./autopilot.db"

from sqlalchemy import create_engine, inspect, text

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        tables = inspect(engine).get_table_names()
        has_alembic = "alembic_version" in tables
        has_users   = "users" in tables
        has_clients = "clients" in tables

    if has_users and not has_alembic:
        # Existing database built by create_all() before Alembic was introduced.
        # Stamp to whichever revision matches what's already in the DB so that
        # only the *new* migrations (new agents, etc.) are applied on upgrade.
        if has_clients:
            stamp = "0021_clients"
        else:
            stamp = "0020_team_runs"
        print(f"[startup] Legacy DB detected (no alembic_version). Stamping to {stamp}...", flush=True)
        os.system(f"alembic stamp {stamp}")
        print("[startup] Stamp done.", flush=True)
    elif has_alembic:
        print("[startup] Alembic version table found — running normal upgrade.", flush=True)
    else:
        print("[startup] Fresh database — running full upgrade from scratch.", flush=True)
except Exception as exc:
    print(f"[startup] DB probe failed ({exc}); attempting upgrade anyway.", flush=True)
PYEOF

echo "[startup] Running: alembic upgrade head"
alembic upgrade head

echo "[startup] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
