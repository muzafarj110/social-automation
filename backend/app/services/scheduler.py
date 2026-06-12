"""
In-process scheduler for autopilot campaigns.

Every tick it finds active campaigns whose `next_run_at` is due and runs them
(generate + schedule/draft the next batch). Zernio owns the actual publish clock,
so this only handles the recurring *generation* top-up.

APScheduler is imported lazily inside start() so importing this module never
requires the dependency (keeps tests and tooling light).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import campaign as cstate
from app.models.campaign import Campaign
from app.services import campaigns as svc

log = logging.getLogger("uvicorn.error")

_scheduler = None
TICK_MINUTES = 15


async def run_due_campaigns() -> int:
    """Run every active, due campaign. Returns how many ran."""
    now = datetime.now(timezone.utc)
    ran = 0
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(Campaign).where(
                Campaign.status == cstate.ACTIVE,
                Campaign.next_run_at.is_not(None),
                Campaign.next_run_at <= now,
            )
        )
        for c in list(rows):
            try:
                await svc.run_campaign(c, db)
                ran += 1
            except Exception as exc:  # one bad campaign shouldn't stop the rest
                log.warning("Campaign %s failed: %s", c.id, exc)
                c.last_error = str(exc)[:500]
                c.next_run_at = now + timedelta(days=1)  # back off, retry tomorrow
                await db.commit()
    return ran


def start() -> None:
    """Start the background scheduler (no-op if APScheduler is unavailable)."""
    global _scheduler
    if _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except Exception as exc:  # dependency missing — degrade gracefully
        log.warning("APScheduler not available; autopilot auto-runs disabled (%s)", exc)
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_due_campaigns, "interval", minutes=TICK_MINUTES,
        id="campaign_topup", coalesce=True, max_instances=1,
    )
    _scheduler.start()
    log.info("Autopilot scheduler started (every %d min).", TICK_MINUTES)


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        finally:
            _scheduler = None
