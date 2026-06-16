#!/bin/sh
# Startup: run Alembic migrations, then start uvicorn.
#
# Handles the legacy case where Railway's Postgres DB was already populated by
# init_db() / create_all() before Alembic migrations were introduced, so
# running upgrade head from scratch would fail with "table X already exists".

echo "[startup] Running: alembic upgrade head"

if alembic upgrade head; then
    echo "[startup] Migrations complete."
else
    echo "[startup] Direct upgrade failed. DB may have pre-Alembic tables."
    echo "[startup] Stamping 0020_team_runs and retrying..."

    # Mark the app as being at 0020 (the last migration before our new agents).
    # This tells Alembic "everything up to 0020 is already applied" so it only
    # runs 0021 (clients) through 0025 (proactive_items) on the next upgrade.
    alembic stamp 0020_team_runs

    echo "[startup] Running: alembic upgrade head (retry)"
    alembic upgrade head
    echo "[startup] Recovery upgrade complete."
fi

echo "[startup] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
