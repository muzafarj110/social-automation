"""Campaigns API — autopilot config CRUD plus a manual run trigger."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.entitlements import plan_limit
from app.db.session import get_db
from app.models import campaign as cstate
from app.models.account import LinkedInAccount
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate
from app.schemas.post import PostOut
from app.services import campaigns as svc

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


async def _owned(campaign_id: int, user: User, db: AsyncSession) -> Campaign:
    c = await db.get(Campaign, campaign_id)
    if not c or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return c


async def _check_account(account_id: int, user: User, db: AsyncSession) -> None:
    acc = await db.get(LinkedInAccount, account_id)
    if not acc or acc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked account not found")


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    body: CampaignCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    await _check_account(body.account_id, current, db)

    # Plan caps (free = a limited taste of Autopilot).
    max_campaigns = plan_limit(current, "max_campaigns")
    if max_campaigns is not None:
        existing = await db.scalar(
            select(func.count(Campaign.id)).where(Campaign.user_id == current.id)
        )
        if (existing or 0) >= max_campaigns:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"Your plan includes {max_campaigns} campaign"
                f"{'s' if max_campaigns != 1 else ''}. Upgrade to run more.",
            )

    data = body.model_dump()
    # Clamp posting cadence to the plan's weekly cap.
    max_per_week = plan_limit(current, "max_posts_per_week")
    if max_per_week is not None and data.get("frequency_per_week", 0) > max_per_week:
        data["frequency_per_week"] = max_per_week

    # next_run_at stays None until the first manual "Run now" — avoids surprise
    # auto-posting right after creation. After the first run it recurs weekly.
    c = Campaign(
        user_id=current.id,
        **data,
        status=cstate.ACTIVE,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Campaign]:
    rows = await db.scalars(
        select(Campaign).where(Campaign.user_id == current.id).order_by(Campaign.created_at.desc())
    )
    return list(rows)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    return await _owned(campaign_id, current, db)


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    c = await _owned(campaign_id, current, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/{campaign_id}", status_code=204, response_model=None)
async def delete_campaign(
    campaign_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    c = await _owned(campaign_id, current, db)
    await db.delete(c)
    await db.commit()


@router.post("/{campaign_id}/run", response_model=list[PostOut])
async def run_campaign_now(
    campaign_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """Manually generate a batch now (handy for testing and first-run)."""
    c = await _owned(campaign_id, current, db)
    try:
        return await svc.run_campaign(c, db)
    except svc.CampaignError as e:
        raise HTTPException(e.status_code, e.message) from e
