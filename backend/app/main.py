"""
LinkedIn Autopilot — FastAPI entrypoint.

Run (from backend/):
    python3 -m pip install -r requirements.txt
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    accounts, admin, analytics, auth, brand, campaigns, content, inbox, posts, profile, routes,
)
from app.core.config import settings
from app.db.session import init_db

log = logging.getLogger("uvicorn.error")

# Built React app (Vite output). In the Docker image this is copied to
# /app/frontend/dist; locally it's <repo>/frontend/dist after `npm run build`.
FRONTEND_DIST = Path(
    os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables on startup. Use Alembic in production.
    await init_db()
    if not settings.hub_api_key or settings.hub_api_key.startswith("paste-"):
        log.warning("HUB_API_KEY not set — generation will need a per-user key.")
    if not settings.zernio_api_key or settings.zernio_api_key.startswith("paste-"):
        log.warning("ZERNIO_API_KEY not set — publishing endpoints unavailable.")
    # Autopilot: recurring campaign top-up (no-op if APScheduler is unavailable).
    from app.services import scheduler
    scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(
    title="LinkedIn Autopilot API",
    version="0.2.0",
    description="Orchestrator: generates via AI Models Hub, acts via Zernio.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# System + open demo
app.include_router(routes.router, prefix="/api")
# Phase 1
app.include_router(auth.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(content.router, prefix="/api")
# Phase 2
app.include_router(posts.router, prefix="/api")
# Phase 4 — approval inbox
app.include_router(inbox.router, prefix="/api")
# Autopilot campaigns
app.include_router(campaigns.router, prefix="/api")
# Analytics + feedback loop
app.include_router(analytics.router, prefix="/api")
# Profile Studio
app.include_router(profile.router, prefix="/api")
# Strategy brain (brand profile)
app.include_router(brand.router, prefix="/api")
# Admin dashboard (operator-only)
app.include_router(admin.router, prefix="/api")


# --- Static frontend (production single-service deploy) ---------------------
# When a built frontend exists, FastAPI serves it on the same origin as the API,
# so no CORS/extra service is needed. When it doesn't (local API-only dev),
# `/` just returns JSON app info.
_ASSETS = FRONTEND_DIST / "assets"
_INDEX = FRONTEND_DIST / "index.html"

if _ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")


@app.get("/", include_in_schema=False)
async def root():
    if _INDEX.is_file():
        return FileResponse(_INDEX)
    return {"app": "LinkedIn Autopilot API", "version": "0.2.0", "docs": "/docs"}


if _INDEX.is_file():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Serve static files, falling back to index.html for client-side routes.
        API paths are handled by the routers above; anything under /api that
        reaches here is a genuine 404."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_INDEX)
