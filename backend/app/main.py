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
    accounts, admin, analytics, auth, billing, brand, campaigns, clients, competitor, connections,
    content, inbox, leads, media, opportunities, posts, proactive, profile, routes, seo_geo,
    social_listening, team, videos,
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
    if not settings.video_agent_enabled:
        log.warning("OPENROUTER_API_KEY / PEXELS_API_KEY not set — video agent unavailable.")
    # Autopilot: recurring campaign top-up (no-op if APScheduler is unavailable).
    from app.services import scheduler
    scheduler.start()
    # User-uploaded media files live here (see also app/api/media.py). Created
    # at startup — not import time — so a missing/unwritable path fails loudly
    # instead of crashing the whole app before the server can even start.
    _UPLOADS.mkdir(parents=True, exist_ok=True)
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
# Billing — usage-based credits (Stripe)
app.include_router(billing.router, prefix="/api")
# Leads — CRM-lite
app.include_router(leads.router, prefix="/api")
# Opportunities — AI "what to act on next"
app.include_router(opportunities.router, prefix="/api")

app.include_router(competitor.router, prefix="/api")
# Proactive feed (auto-generated agent work)
app.include_router(proactive.router, prefix="/api")
# Social Listening agent
app.include_router(social_listening.router, prefix="/api")
# SEO + GEO agent
app.include_router(seo_geo.router, prefix="/api")
# Content Team — agentic weekly content cycle
app.include_router(team.router, prefix="/api")
# Clients — agency multi-client workspaces
app.include_router(clients.router, prefix="/api")
# Channel connections — WhatsApp Business + Telegram
app.include_router(connections.router, prefix="/api")
# Media uploads
app.include_router(media.router, prefix="/api")
# Video agent — Faceless Video Pipeline integration
app.include_router(videos.router, prefix="/api")


# --- Static frontend (production single-service deploy) ---------------------
# When a built frontend exists, FastAPI serves it on the same origin as the API,
# so no CORS/extra service is needed. When it doesn't (local API-only dev),
# `/` just returns JSON app info.
_ASSETS = FRONTEND_DIST / "assets"
_INDEX = FRONTEND_DIST / "index.html"

if _ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

# User-uploaded media files (images/videos attached to posts).
# Files live in settings.upload_dir — "/app/uploads" on Railway (ephemeral
# across deploys, fine for beta) or "./uploads" locally by default. The
# directory itself is created at startup in `lifespan`, not here at import
# time, so an unwritable path doesn't crash the app before it can boot.
_UPLOADS = Path(settings.upload_dir)
# check_dir=False: the directory is created in `lifespan` (below), which runs
# after this module-level mount call, so it may not exist yet at import time.
app.mount("/uploads", StaticFiles(directory=_UPLOADS, check_dir=False), name="uploads")


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
