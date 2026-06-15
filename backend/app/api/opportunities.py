"""
Opportunities API — the AI marketing team's "what to act on next".

Derived from the user's OWN data (accounts, brand, posts, inbox, leads), so it's
fast, free (no credit spend), and always isolated to that user. Each opportunity
carries an impact level and an action that routes to the right place in the app.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import post as post_status
from app.models.account import LinkedInAccount
from app.models.approval import PENDING, Approval
from app.models.brand import BrandProfile
from app.models.lead import NEW, Lead
from app.models.post import Post
from app.models.user import User

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


async def _count(db: AsyncSession, stmt) -> int:
    return int(await db.scalar(stmt) or 0)


@router.get("")
async def list_opportunities(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = current.id
    accounts = await _count(db, select(func.count(LinkedInAccount.id)).where(LinkedInAccount.user_id == uid))
    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == uid))
    brand_ready = bool(brand and (brand.voice or brand.brand_name))
    pending = await _count(db, select(func.count(Approval.id)).where(Approval.user_id == uid, Approval.status == PENDING))
    new_leads = await _count(db, select(func.count(Lead.id)).where(Lead.user_id == uid, Lead.status == NEW))
    scheduled = await _count(db, select(func.count(Post.id)).where(Post.user_id == uid, Post.status == post_status.SCHEDULED))
    drafts = await _count(db, select(func.count(Post.id)).where(Post.user_id == uid, Post.status == post_status.DRAFT))
    last_pub = await db.scalar(
        select(func.max(Post.updated_at)).where(Post.user_id == uid, Post.status == post_status.PUBLISHED)
    )

    ops: list[dict] = []

    def add(oid, tag, title, desc, impact, label, tab):
        ops.append({
            "id": oid, "tag": tag, "title": title, "desc": desc,
            "impact": impact, "action_label": label, "action_tab": tab,
        })

    if accounts == 0:
        add("connect", "Setup", "Connect your channels",
            "Link a social account so Autopilot can publish for you.",
            "high", "Connect", "accounts")
    if not brand_ready:
        add("brand", "Setup", "Define your brand voice",
            "Set your voice and audience so every post sounds like you.",
            "medium", "Set up brand", "strategy")
    if pending:
        add("approvals", "Needs review",
            f"{pending} draft{'s' if pending != 1 else ''} awaiting approval",
            "AI has drafts ready for you to approve and send.",
            "high", "Open inbox", "inbox")
    if new_leads:
        add("leads", "Lead signal",
            f"{new_leads} lead{'s' if new_leads != 1 else ''} need outreach",
            "New leads with no outreach yet — let AI draft it.",
            "high", "Review leads", "leads")

    if accounts > 0:
        if last_pub is None:
            add("first_post", "Timing gap", "Publish your first post",
                "You're connected but haven't published yet. Start strong.",
                "high", "Create a post", "generate")
        else:
            now = datetime.now(timezone.utc)
            lp = last_pub if last_pub.tzinfo else last_pub.replace(tzinfo=timezone.utc)
            days = (now - lp).days
            if days >= 4:
                add("timing", "Timing gap", f"You haven't posted in {days} days",
                    "Consistency drives reach. Fill the gap with a fresh post.",
                    "medium", "Create a post", "generate")

    if accounts > 0 and scheduled == 0:
        add("queue", "Timing gap", "Nothing scheduled ahead",
            "Set up an autopilot campaign so your queue stays full.",
            "medium", "Set up autopilot", "campaigns")
    if drafts:
        add("drafts", "Repurpose",
            f"{drafts} draft{'s' if drafts != 1 else ''} ready to publish",
            "You have drafts waiting — publish or schedule them.",
            "medium", "Open posts", "posts")

    order = {"high": 0, "medium": 1, "low": 2}
    ops.sort(key=lambda o: order.get(o["impact"], 1))
    return {"opportunities": ops, "scanned_at": datetime.now(timezone.utc).isoformat()}
