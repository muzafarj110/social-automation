"""
Billing API — hybrid: monthly subscription plans + one-time credit top-ups, via Stripe.

- Subscriptions (recurring): a tier grants a monthly credit allowance that RESETS
  each cycle. Granted on Stripe's `invoice.paid` webhook.
- Top-ups (one-time): credit packs added on `checkout.session.completed`.

GET /billing shows balance, current plan, available plans + top-up packs.
POST /billing/checkout starts Checkout (subscription or payment, by price id).
POST /billing/portal opens Stripe's hosted portal to manage/cancel a subscription.

Degrades gracefully: with no STRIPE_SECRET_KEY, billing simply reports disabled.
All Price IDs (and prices) live in Stripe + env, never hardcoded.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

log = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    price_id: str


def _stripe():
    """Import + configure the Stripe SDK, or None if billing isn't set up."""
    if not settings.billing_enabled:
        return None
    try:
        import stripe
    except Exception:  # SDK not installed
        return None
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _epoch_to_dt(ts) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


async def _user_by_customer(db: AsyncSession, customer_id: str | None) -> User | None:
    if not customer_id:
        return None
    res = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    return res.scalar_one_or_none()


@router.get("")
async def billing_overview(current: User = Depends(get_current_user)) -> dict:
    """Balance, current subscription, and the plans / top-up packs available."""
    plans = [
        {"price_id": pid, "tier": p["tier"], "credits": p["credits"]}
        for pid, p in settings.plans().items()
    ]
    packs = [{"price_id": pid, "credits": amt} for pid, amt in settings.credit_packs().items()]
    sub = None
    if current.subscription_tier:
        sub = {
            "tier": current.subscription_tier,
            "status": current.subscription_status,
            "renews_at": current.subscription_renews_at.isoformat()
            if current.subscription_renews_at else None,
        }
    return {
        "enabled": settings.billing_enabled,
        "subscriptions_enabled": settings.subscriptions_enabled,
        "credits": current.credits,
        "plans": plans,
        "packs": packs,
        "subscription": sub,
    }


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start Checkout. Subscription if the price is a plan, else a one-time pack."""
    stripe = _stripe()
    if stripe is None:
        raise HTTPException(503, "Billing isn't configured yet.")

    plans = settings.plans()
    packs = settings.credit_packs()
    is_plan = body.price_id in plans
    is_pack = body.price_id in packs
    if not (is_plan or is_pack):
        raise HTTPException(400, "Unknown plan or pack.")

    success = settings.billing_success_url or "https://example.com/billing?ok=1"
    cancel = settings.billing_cancel_url or "https://example.com/billing?cancel=1"

    try:
        if is_plan:
            # Subscriptions need a Stripe customer so renewals/portal attach to the user.
            if not current.stripe_customer_id:
                cust = stripe.Customer.create(
                    email=current.email, metadata={"user_id": str(current.id)}
                )
                current.stripe_customer_id = cust.id
                await db.commit()
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=current.stripe_customer_id,
                line_items=[{"price": body.price_id, "quantity": 1}],
                success_url=success,
                cancel_url=cancel,
                client_reference_id=str(current.id),
                metadata={"user_id": str(current.id), "tier": plans[body.price_id]["tier"]},
            )
        else:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{"price": body.price_id, "quantity": 1}],
                success_url=success,
                cancel_url=cancel,
                client_reference_id=str(current.id),
                metadata={"user_id": str(current.id), "credits": str(packs[body.price_id])},
            )
    except Exception as e:  # surface a clean message, log the detail
        log.warning("Stripe checkout failed: %s", e)
        raise HTTPException(502, "Couldn't start checkout — please try again.") from e
    return {"ok": True, "url": session.url}


@router.post("/portal")
async def billing_portal(current: User = Depends(get_current_user)) -> dict:
    """Open Stripe's hosted billing portal to manage or cancel a subscription."""
    stripe = _stripe()
    if stripe is None:
        raise HTTPException(503, "Billing isn't configured yet.")
    if not current.stripe_customer_id:
        raise HTTPException(400, "No subscription to manage yet.")
    return_url = settings.billing_success_url or "https://example.com/billing"
    try:
        session = stripe.billing_portal.Session.create(
            customer=current.stripe_customer_id, return_url=return_url
        )
    except Exception as e:
        log.warning("Stripe portal failed: %s", e)
        raise HTTPException(502, "Couldn't open the billing portal — please try again.") from e
    return {"url": session.url}


def _plan_for_price(price_id: str | None) -> dict | None:
    if not price_id:
        return None
    return settings.plans().get(price_id)


async def _apply_subscription(
    db: AsyncSession, user: User, *, price_id: str | None,
    status: str | None, renews_at: datetime | None, grant_credits: bool,
) -> None:
    """Update a user's subscription state; optionally reset monthly credits."""
    plan = _plan_for_price(price_id)
    if plan:
        user.subscription_tier = plan["tier"]
        if grant_credits:
            user.credits = plan["credits"]  # monthly reset to allowance
    if status:
        user.subscription_status = status
    if renews_at:
        user.subscription_renews_at = renews_at
    await db.commit()


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Stripe webhook — verify signature, then apply credits / subscription state."""
    stripe = _stripe()
    if stripe is None:
        raise HTTPException(503, "Billing isn't configured.")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception as e:  # bad signature / malformed
        log.warning("Stripe webhook verification failed: %s", e)
        raise HTTPException(400, "Invalid webhook signature.") from e

    etype = event.get("type")
    obj = event["data"]["object"]

    # One-time credit pack purchased (subscriptions credit via invoice.paid below).
    if etype == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        if obj.get("mode") == "subscription":
            # Attach the Stripe customer to the user; tier/credits land on invoice.paid.
            user_id = meta.get("user_id") or obj.get("client_reference_id")
            customer_id = obj.get("customer")
            if user_id and customer_id:
                user = await db.get(User, int(user_id))
                if user is not None and not user.stripe_customer_id:
                    user.stripe_customer_id = customer_id
                    if meta.get("tier"):
                        user.subscription_tier = meta["tier"]
                    await db.commit()
        else:
            user_id = meta.get("user_id") or obj.get("client_reference_id")
            try:
                credits_to_add = int(meta.get("credits") or 0)
            except (TypeError, ValueError):
                credits_to_add = 0
            if user_id and credits_to_add > 0:
                user = await db.get(User, int(user_id))
                if user is not None:
                    user.credits += credits_to_add  # top-ups stack on current balance
                    await db.commit()
                    log.info("Added %d top-up credits to user %s", credits_to_add, user_id)

    # Monthly renewal (and first charge): reset credits to the tier's allowance.
    elif etype in ("invoice.paid", "invoice.payment_succeeded"):
        user = await _user_by_customer(db, obj.get("customer"))
        if user is not None:
            line = ((obj.get("lines") or {}).get("data") or [{}])[0]
            price_id = ((line.get("price") or {}).get("id"))
            renews = _epoch_to_dt((line.get("period") or {}).get("end"))
            await _apply_subscription(
                db, user, price_id=price_id, status="active",
                renews_at=renews, grant_credits=True,
            )
            log.info("Renewed subscription credits for user %s", user.id)

    # Plan change / status update (upgrade, downgrade, past_due, cancel-at-period-end).
    elif etype == "customer.subscription.updated":
        user = await _user_by_customer(db, obj.get("customer"))
        if user is not None:
            item = ((obj.get("items") or {}).get("data") or [{}])[0]
            price_id = ((item.get("price") or {}).get("id"))
            await _apply_subscription(
                db, user, price_id=price_id, status=obj.get("status"),
                renews_at=_epoch_to_dt(obj.get("current_period_end")), grant_credits=False,
            )

    # Subscription fully ended.
    elif etype == "customer.subscription.deleted":
        user = await _user_by_customer(db, obj.get("customer"))
        if user is not None:
            user.subscription_status = "canceled"
            user.subscription_tier = None
            await db.commit()

    return {"received": True}
