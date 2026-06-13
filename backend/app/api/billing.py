"""
Billing API — usage-based credits via Stripe.

Flow: GET /billing shows balance + available credit packs. POST /billing/checkout
creates a Stripe Checkout session for a pack and returns its URL. Stripe calls
POST /billing/webhook on payment; we verify the signature and add credits.

Everything degrades gracefully: if STRIPE_SECRET_KEY isn't set, the endpoints
report billing as disabled instead of erroring, so the app runs without Stripe.
Stripe Price IDs (and therefore prices) live in Stripe + env, never hardcoded.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
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


@router.get("")
async def billing_overview(current: User = Depends(get_current_user)) -> dict:
    """The user's credit balance and the packs they can buy."""
    packs = [{"price_id": pid, "credits": amt} for pid, amt in settings.credit_packs().items()]
    return {
        "enabled": settings.billing_enabled,
        "credits": current.credits,
        "packs": packs,
    }


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    current: User = Depends(get_current_user),
) -> dict:
    """Create a Stripe Checkout session for a credit pack; returns its URL."""
    stripe = _stripe()
    if stripe is None:
        raise HTTPException(503, "Billing isn't configured yet.")
    packs = settings.credit_packs()
    if body.price_id not in packs:
        raise HTTPException(400, "Unknown credit pack.")
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": body.price_id, "quantity": 1}],
            success_url=settings.billing_success_url or "https://example.com/billing?ok=1",
            cancel_url=settings.billing_cancel_url or "https://example.com/billing?cancel=1",
            client_reference_id=str(current.id),
            metadata={"user_id": str(current.id), "credits": str(packs[body.price_id])},
        )
    except Exception as e:  # surface a clean message, log the detail
        log.warning("Stripe checkout failed: %s", e)
        raise HTTPException(502, "Couldn't start checkout — please try again.") from e
    return {"ok": True, "url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Stripe payment webhook — verifies the signature, then credits the user."""
    stripe = _stripe()
    if stripe is None:
        raise HTTPException(503, "Billing isn't configured.")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as e:  # bad signature / malformed
        log.warning("Stripe webhook verification failed: %s", e)
        raise HTTPException(400, "Invalid webhook signature.") from e

    if event.get("type") == "checkout.session.completed":
        obj = event["data"]["object"]
        meta = obj.get("metadata") or {}
        user_id = meta.get("user_id") or obj.get("client_reference_id")
        try:
            credits_to_add = int(meta.get("credits") or 0)
        except (TypeError, ValueError):
            credits_to_add = 0
        if user_id and credits_to_add > 0:
            user = await db.get(User, int(user_id))
            if user is not None:
                user.credits += credits_to_add
                await db.commit()
                log.info("Added %d credits to user %s", credits_to_add, user_id)

    return {"received": True}
