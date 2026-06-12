"""
Approval inbox API — the human-in-the-loop queue.

generate → Hub drafts an action and queues it (pending)
list/get → review pending drafts
edit     → tweak the draft text before approving
approve  → company-page comment replies execute via Zernio (sent); everything
           else is marked ready for the human to send/apply (approved/manual)
reject   → discard
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.clients.hub_client import (
    HubAuthError,
    HubError,
    HubPermissionError,
    HubRateLimitError,
    HubValidationError,
)
from app.clients.zernio_client import ZernioError
from app.core.user_keys import resolve_zernio_key
from app.db.session import get_db
from app.models import approval as st
from app.models.account import LinkedInAccount
from app.models.approval import Approval
from app.models.user import User
from app.schemas.approval import (
    ApprovalOut,
    EditApprovalRequest,
    GenerateApprovalRequest,
)
from app.services import approvals as svc

router = APIRouter(prefix="/inbox", tags=["inbox"])


async def _get_owned(approval_id: int, user: User, db: AsyncSession) -> Approval:
    a = await db.get(Approval, approval_id)
    if not a or a.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    return a


@router.post("/generate", response_model=ApprovalOut, status_code=201)
async def generate(
    body: GenerateApprovalRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Approval:
    if body.account_id is not None:
        acc = await db.get(LinkedInAccount, body.account_id)
        if not acc or acc.user_id != current.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked account not found")

    try:
        ai_payload, draft_text = await svc.generate_draft(current, body.kind, body.params)
    except svc.DraftError as e:
        raise HTTPException(e.status_code, e.message) from e
    except HubRateLimitError as e:
        raise HTTPException(429, e.message) from e
    except HubAuthError as e:
        raise HTTPException(401, e.message) from e
    except HubPermissionError as e:
        raise HTTPException(403, e.message) from e
    except HubValidationError as e:
        raise HTTPException(400, e.message) from e
    except HubError as e:
        raise HTTPException(502, f"Hub error: {e.message}") from e

    approval = Approval(
        user_id=current.id,
        account_id=body.account_id,
        kind=body.kind,
        ai_payload=ai_payload,
        draft_text=draft_text,
        context=body.context,
        status=st.PENDING,
    )
    db.add(approval)
    await db.flush()

    # Compliant auto-send: only company-page comment replies can post without a
    # human (LinkedIn's API allows it). Everything else stays a pending draft.
    ctx = body.context or {}
    if body.auto_send and body.kind == st.COMMENT and ctx.get("comment_id"):
        try:
            await svc.reply_company_comment(
                str(ctx["comment_id"]), draft_text or "",
                zernio_key=resolve_zernio_key(current) or "",
            )
            approval.status = st.SENT
            approval.executed_via = st.ZERNIO
            approval.resolved_at = datetime.now(timezone.utc)
        except (svc.DraftError, ZernioError) as e:
            # leave it pending so the user can review/send manually
            approval.error = getattr(e, "message", str(e))

    await db.commit()
    await db.refresh(approval)
    return approval


@router.get("", response_model=list[ApprovalOut])
async def list_inbox(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query("pending", alias="status"),
) -> list[Approval]:
    stmt = (
        select(Approval)
        .where(Approval.user_id == current.id)
        .order_by(Approval.created_at.desc())
    )
    if status_filter and status_filter != "all":
        stmt = stmt.where(Approval.status == status_filter)
    rows = await db.scalars(stmt)
    return list(rows)


@router.get("/{approval_id}", response_model=ApprovalOut)
async def get_one(
    approval_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Approval:
    return await _get_owned(approval_id, current, db)


@router.patch("/{approval_id}", response_model=ApprovalOut)
async def edit(
    approval_id: int,
    body: EditApprovalRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Approval:
    a = await _get_owned(approval_id, current, db)
    if a.status != st.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only pending drafts can be edited")
    a.draft_text = body.draft_text
    await db.commit()
    await db.refresh(a)
    return a


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
async def approve(
    approval_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Approval:
    a = await _get_owned(approval_id, current, db)
    if a.status != st.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Approval is already {a.status}")

    ctx = a.context or {}
    comment_id = ctx.get("comment_id")

    # Compliant path: company-page comment reply executes via Zernio.
    if a.kind == st.COMMENT and comment_id:
        try:
            await svc.reply_company_comment(
                str(comment_id), a.draft_text or "",
                zernio_key=resolve_zernio_key(current) or "",
            )
        except svc.DraftError as e:
            raise HTTPException(e.status_code, e.message) from e
        except ZernioError as e:
            a.error = e.message
            await db.commit()
            raise HTTPException(e.status_code or 502, e.message) from e
        a.status = st.SENT
        a.executed_via = st.ZERNIO
    else:
        # No official API → ready for the human to send/apply.
        a.status = st.APPROVED
        a.executed_via = st.MANUAL

    a.error = None
    a.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(a)
    return a


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
async def reject(
    approval_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Approval:
    a = await _get_owned(approval_id, current, db)
    if a.status not in (st.PENDING, st.APPROVED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot reject a {a.status} item")
    a.status = st.REJECTED
    a.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(a)
    return a
