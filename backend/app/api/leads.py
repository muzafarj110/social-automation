"""
Leads API — CRM-lite for lead-gen.

Capture leads, track them through a simple pipeline, and let AI draft outreach
using an existing Hub model. Drafting is a billed AI action (one credit).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.hub_client import HubClient, HubError
from app.core import credits
from app.core.config import settings
from app.core.hub_errors import hub_http
from app.core.user_keys import resolve_hub_key
from app.db.session import get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import DraftOutreachRequest, LeadCreate, LeadOut, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])

# Free-form keys the Hub may use for the drafted message.
_DRAFT_KEYS = ("message", "dm", "outreach", "draft", "full_message", "text", "content", "result")


async def _owned(lead_id: int, user: User, db: AsyncSession) -> Lead:
    lead = await db.get(Lead, lead_id)
    if not lead or lead.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    return lead


@router.get("", response_model=list[LeadOut])
async def list_leads(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Lead]:
    rows = await db.scalars(
        select(Lead).where(Lead.user_id == current.id).order_by(Lead.created_at.desc())
    )
    return list(rows)


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(
    body: LeadCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    lead = Lead(user_id=current.id, **body.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int,
    body: LeadUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    lead = await _owned(lead_id, current, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204, response_model=None)
async def delete_lead(
    lead_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    lead = await _owned(lead_id, current, db)
    await db.delete(lead)
    await db.commit()


@router.post("/{lead_id}/draft-outreach", response_model=LeadOut)
async def draft_outreach(
    lead_id: int,
    body: DraftOutreachRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Lead:
    """AI-draft a personalized outreach message for this lead (1 credit)."""
    lead = await _owned(lead_id, current, db)
    if not credits.has_credits(current, credits.COST_GENERATE):
        raise HTTPException(402, "You're out of credits. Top up under Billing to keep creating.")
    key = resolve_hub_key(current)
    if not key:
        raise HTTPException(400, "No Hub API key on file — set one in the app first.")

    payload = {
        "recipient": lead.name,
        "context": lead.notes or f"A lead from {lead.source or lead.platform or 'your audience'}.",
        "angle": body.angle,
        "goal": body.goal,
    }
    async with HubClient(settings.hub_base_url, key) as hub:
        try:
            data = await hub.call("dm_writer", payload)
        except HubError as e:
            raise hub_http(e) from e

    draft = None
    for k in _DRAFT_KEYS:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            draft = v.strip()
            break
    lead.draft = draft or "Couldn't draft a message — try again."
    await credits.charge(db, current, credits.COST_GENERATE)
    await db.refresh(lead)
    return lead
