"""Posts API — create drafts, then publish now or schedule via Zernio."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import post as post_status
from app.models.account import LinkedInAccount
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostOut, PostUpdate, ScheduleRequest
from app.services import publisher

router = APIRouter(prefix="/posts", tags=["posts"])


async def _get_owned_post(post_id: int, user: User, db: AsyncSession) -> Post:
    post = await db.get(Post, post_id)
    if not post or post.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    return post


async def _get_owned_account(account_id: int, user: User, db: AsyncSession) -> LinkedInAccount:
    account = await db.get(LinkedInAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked account not found")
    return account


@router.post("", response_model=PostOut, status_code=201)
async def create_post(
    body: PostCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    await _get_owned_account(body.account_id, current, db)  # ownership check
    post = Post(
        user_id=current.id,
        account_id=body.account_id,
        body=body.body,
        hashtags=body.hashtags,
        media=body.media,
        first_comment=body.first_comment,
        status=post_status.DRAFT,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("", response_model=list[PostOut])
async def list_posts(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
) -> list[Post]:
    stmt = select(Post).where(Post.user_id == current.id).order_by(Post.created_at.desc())
    if status_filter:
        stmt = stmt.where(Post.status == status_filter)
    rows = await db.scalars(stmt)
    return list(rows)


@router.get("/{post_id}", response_model=PostOut)
async def get_post(
    post_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    return await _get_owned_post(post_id, current, db)


@router.patch("/{post_id}", response_model=PostOut)
async def update_post(
    post_id: int,
    body: PostUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    post = await _get_owned_post(post_id, current, db)
    if post.status == post_status.PUBLISHED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot edit a published post")
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(post, field, value)
    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    post = await _get_owned_post(post_id, current, db)
    await db.delete(post)
    await db.commit()


@router.post("/{post_id}/publish", response_model=PostOut)
async def publish_post(
    post_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    post = await _get_owned_post(post_id, current, db)
    if post.status == post_status.PUBLISHED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Post already published")
    account = await _get_owned_account(post.account_id, current, db)

    try:
        await publisher.publish_now(post, account.zernio_account_id)
    except publisher.PublishError as e:
        await db.commit()  # persist FAILED status/error set by the service
        raise HTTPException(e.status_code, e.message) from e

    await db.commit()
    await db.refresh(post)
    return post


@router.post("/{post_id}/schedule", response_model=PostOut)
async def schedule_post(
    post_id: int,
    body: ScheduleRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    post = await _get_owned_post(post_id, current, db)
    if post.status == post_status.PUBLISHED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Post already published")
    account = await _get_owned_account(post.account_id, current, db)

    try:
        await publisher.schedule(post, account.zernio_account_id,
                                 body.scheduled_for, body.timezone)
    except publisher.PublishError as e:
        await db.commit()
        raise HTTPException(e.status_code, e.message) from e

    await db.commit()
    await db.refresh(post)
    return post
