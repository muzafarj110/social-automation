"""
LinkedIn Autopilot — FastAPI entrypoint.

Run (from backend/):
    python3 -m pip install -r requirements.txt
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, auth, content, posts, routes
from app.core.config import settings
from app.db.session import init_db

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables on startup. Use Alembic in production.
    await init_db()
    if not settings.hub_api_key or settings.hub_api_key.startswith("paste-"):
        log.warning("HUB_API_KEY not set — generation will need a per-user key.")
    if not settings.zernio_api_key or settings.zernio_api_key.startswith("paste-"):
        log.warning("ZERNIO_API_KEY not set — publishing endpoints unavailable.")
    yield


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


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"app": "LinkedIn Autopilot API", "version": "0.2.0", "docs": "/docs"}
