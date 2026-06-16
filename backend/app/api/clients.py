"""Clients API — an agency manages multiple client workspaces and switches between them."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


def _out(c: Client) -> dict:
    return {"id": c.id, "name": c.name, "brand_name": c.brand_name,
            "created_at": c.created_at.isoformat() if c.created_at else None}


async def _owned(client_id: int, user: User, db: AsyncSession) -> Client:
    c = await db.get(Client, client_id)
    if not c or c.agency_user_id != user.id:
        raise HTTPException(404, "Client not found.")
    return c


@router.get("")
async def list_clients(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = list(await db.scalars(
        select(Client).where(Client.agency_user_id == current.id).order_by(Client.name)
    ))
    return {"clients": [_out(c) for c in rows], "active_client_id": current.active_client_id}


@router.post("", status_code=201)
async def create_client(
    body: ClientCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    c = Client(agency_user_id=current.id, name=body.name.strip())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    # Switch into the new client immediately.
    current.active_client_id = c.id
    await db.commit()
    return _out(c)


@router.post("/{client_id}/activate")
async def activate_client(
    client_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _owned(client_id, current, db)
    current.active_client_id = client_id
    await db.commit()
    return {"active_client_id": client_id}


@router.post("/deactivate")
async def deactivate_client(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Switch back to the agency's own/default workspace."""
    current.active_client_id = None
    await db.commit()
    return {"active_client_id": None}
