"""
Proactive feed API — serve and manage auto-generated agent work items.

GET  /proactive          list recent non-dismissed items for the current user
POST /proactive/generate trigger an immediate generation (useful for testing / first-load)
POST /proactive/{id}/dismiss  mark an item as dismissed
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.proactive import ProactiveItem
from app.models.user import User
from app.schemas.proactive import ProactiveItemOut
from app.services.proactive import generate_for_user

router = APIRouter(prefix="/proactive", tags=["proactive"])

_FEED_WINDOW_HOURS = 48  # show items generated in the last 48 hours


def _serialize(p: ProactiveItem) -> dict:
    return {
        "id": p.id, "agent": p.agent, "title": p.title, "body": p.body,
        "action_tab": p.action_tab, "status": p.status, "generated_at": p.generated_at,
    }


@router.get("", response_model=list[ProactiveItemOut])
async def list_proactive(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_FEED_WINDOW_HOURS)
    rows = await db.scalars(
        select(ProactiveItem)
        .where(ProactiveItem.user_id == current.id)
        .where(ProactiveItem.generated_at > cutoff)
        .where(ProactiveItem.status != "dismissed")
        .order_by(ProactiveItem.generated_at.desc())
        .limit(10)
    )
    return [_serialize(p) for p in rows]


@router.post("/generate", response_model=ProactiveItemOut | None)
async def trigger_generate(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict | None:
    """Immediately generate one proactive item (respects the per-window cap)."""
    item = await generate_for_user(current, db)
    return _serialize(item) if item else None


@router.post("/{pid}/dismiss", response_model=ProactiveItemOut)
async def dismiss_item(
    pid: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    p = await db.get(ProactiveItem, pid)
    if p and p.user_id == current.id:
        p.status = "dismissed"
        await db.commit()
        await db.refresh(p)
    return _serialize(p) if p else {}
