# LinkedIn Autopilot — Backend

FastAPI orchestrator. Generates content via the AI Models Hub, acts on LinkedIn
via Zernio. See `../ARCHITECTURE.md` for the full design.

## Setup (one time)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in real values (see below)
```

Generate a strong `JWT_SECRET` for `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Leave `DATABASE_URL` empty for local dev — the app falls back to a SQLite file
(`autopilot.db`). Set it to your Railway Postgres URL in production.

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
# API docs: http://127.0.0.1:8000/docs
```

On startup the app auto-creates tables **only** on the SQLite dev DB. With a
real `DATABASE_URL` set, schema is owned by Alembic (see below).

## Tests

The suite is self-contained: it spins up the ASGI app against a throwaway SQLite
DB and mocks Zernio, so no network or external keys are needed.

```bash
source .venv/bin/activate
python -m pytest -v
```

Covers: auth/account flow, posts publish/schedule, and both API clients
(`HubClient`, `ZernioClient`).

## Database migrations (Alembic)

Schema source of truth for Postgres. Alembic reads the DB URL from `.env` via
`alembic/env.py`, so there's no URL duplicated in `alembic.ini`.

```bash
source .venv/bin/activate

# Apply all migrations (fresh Postgres or SQLite):
alembic upgrade head

# After changing models, generate a new revision:
alembic revision --autogenerate -m "add approvals table"
alembic upgrade head
```

**Already have a dev `autopilot.db` created by the app's auto-create?** It has no
Alembic version stamp. Mark it as current so Alembic doesn't try to recreate
existing tables:

```bash
alembic stamp head
```

The baseline migration (`alembic/versions/20260610_0001_initial_schema.py`)
matches the current `users`, `linkedin_accounts`, and `posts` models.
