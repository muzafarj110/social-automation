# Subscriptions setup (monthly plans + credits)

Hybrid billing: **monthly subscription plans** that each grant a credit allowance which
**resets every cycle**, plus optional **one-time top-ups** (your existing credit packs).
Do it in Stripe **Test mode** first, then flip to Live.

Agreed plans (you set the exact prices in Stripe):

| Tier | Price (you set) | Monthly credits |
|---|---|---|
| Starter | $19 / mo | 100 |
| Growth (most popular) | $49 / mo | 400 |
| Pro | $99 / mo | 1,200 |

## 1. Create 3 recurring prices
For each tier: Product catalog → **+ Add product** → name it (e.g. "Growth") →
Pricing model **Recurring**, billing period **Monthly**, set the price → Save →
open the product and copy the **Price ID** (`price_…`). These must be **recurring**
prices (not one-time).

## 2. Set the plans env var
Build `STRIPE_PLANS` as `priceId:tier:credits`, comma-separated (order = display order;
the middle one is auto-tagged "Most popular"):
```
price_STARTER:starter:100,price_GROWTH:growth:400,price_PRO:pro:1200
```
Add it in Railway → your app service → **Variables** (alongside the existing `STRIPE_*`
vars). One-time top-ups still use `STRIPE_CREDIT_PACKS` as before (optional).

## 3. Enable the Customer Portal
Stripe → Settings → **Billing → Customer portal** → activate it (allow customers to
cancel / switch plans). This powers the in-app **Manage plan** button.

## 4. Add the subscription webhook events
On your existing webhook endpoint
(`/api/billing/webhook`), add these events (keep `checkout.session.completed`):
- `invoice.paid` — grants/reset the monthly credit allowance each cycle
- `customer.subscription.updated` — plan changes / status (past_due, cancel-at-period-end)
- `customer.subscription.deleted` — subscription ended

(The signing secret `STRIPE_WEBHOOK_SECRET` is unchanged.)

## 5. Deploy + migrate
Deploy the app (Railway runs `alembic upgrade head` on start, applying migration
`0018_user_subscriptions`, which adds the subscription columns to `users`).

## 6. Test
- Open **Billing** → the three plans show as tier cards.
- Subscribe with the test card `4242 4242 4242 4242` (any future expiry / CVC / ZIP).
- After payment you're redirected back; `invoice.paid` sets your credits to the tier's
  allowance and shows your plan + renewal date.
- Click **Manage plan** → Stripe portal opens to switch/cancel.

## Notes
- **Reset, not rollover:** each renewal sets credits to the tier allowance (unused credits
  don't carry over). One-time top-ups are added on top and also reset at the next renewal.
- Until `STRIPE_PLANS` is set, the plans section shows "not switched on yet" — nothing breaks.
- Test and Live are fully separate (test prices/webhook only work in test mode).
- Feature gating still uses the existing `plan` field; tiers here govern the **credit
  allowance**. If you later want tiers to unlock features, we can map tier → entitlements.
