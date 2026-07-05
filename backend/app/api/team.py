"""Content Team API — run a cycle, review the batch, approve once to schedule."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.clients import client_scope
from app.db.session import get_db
from app.models.post import Post
from app.models.team_run import TeamRun
from app.models.user import User
from app.schemas.post import PostOut
from app.services import team

router = APIRouter(prefix="/team", tags=["team"])


class PlanRequest(BaseModel):
    count: int = Field(3, ge=1, le=7)
    directive: str | None = None


class RunRequest(BaseModel):
    count: int = Field(3, ge=1, le=7)
    brief: str | None = None
    topics: list[str] | None = None


async def _payload(db: AsyncSession, run: TeamRun) -> dict:
    posts = list(await db.scalars(
        select(Post).where(Post.team_run_id == run.id).order_by(Post.id)
    ))
    return {
        "id": run.id,
        "status": run.status,
        "brief": run.brief,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "posts": [PostOut.model_validate(p).model_dump(mode="json") for p in posts],
    }


async def _owned_run(run_id: int, user: User, db: AsyncSession) -> TeamRun:
    run = await db.get(TeamRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(404, "Run not found.")
    return run


@router.post("/plan")
async def plan(
    body: PlanRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Strategist only: return an editable brief + topics (no posts, no credit)."""
    try:
        brief, topics, learning = await team.build_plan(db, current, body.count, directive=body.directive)
    except team.TeamError as e:
        raise HTTPException(e.status_code, e.message) from e
    return {"brief": brief, "topics": topics, "learning": learning}


@router.post("/run")
async def run(
    body: RunRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        r = await team.run_cycle(db, current, count=body.count, brief=body.brief, topics=body.topics)
    except team.TeamError as e:
        raise HTTPException(e.status_code, e.message) from e
    return await _payload(db, r)


@router.get("/runs")
async def list_runs(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    runs = list(await db.scalars(
        select(TeamRun)
        .where(TeamRun.user_id == current.id, client_scope(TeamRun.client_id, current.active_client_id))
        .order_by(TeamRun.created_at.desc())
    ))
    return [{
        "id": r.id, "status": r.status, "brief": r.brief,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in runs]


@router.get("/runs/{run_id}")
async def get_run(
    run_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await _payload(db, await _owned_run(run_id, current, db))


@router.post("/runs/{run_id}/approve")
async def approve(
    run_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _owned_run(run_id, current, db)
    try:
        r, scheduled, errors = await team.approve_run(db, current, run_id)
    except team.TeamError as e:
        raise HTTPException(e.status_code, e.message) from e
    payload = await _payload(db, r)
    payload["scheduled"] = scheduled
    payload["errors"] = errors
    return payload
