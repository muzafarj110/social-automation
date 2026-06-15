# Connect Stripe (usage-based credits)

The app sells **credit packs** as one-time payments. You define the packs in Stripe and
paste 4 values into Railway. Do it in **Test mode** first, then flip to Live.

## 1. Stripe account
- Sign up / log in at dashboard.stripe.com.
- Keep the **Test mode** toggle ON (top-right) while setting up.

## 2. Get your secret key
- Developers → API keys → reveal **Secret key**.
- Test: starts with `sk_test_…`  · Live: `sk_live_…`
- Copy it → this is `STRIPE_SECRET_KEY`.

## 3. Create credit packs (Products → Prices)
For each pack:
- Product catalog → **+ Add product**.
- Name it, e.g. `100 credits`.
- Pricing model: **One-time** (NOT recurring — our checkout is one-time payment).
- Set the price (e.g. $19) + currency → Save.
- Open the product → copy the **Price ID** (`price_…`).
- Repeat for each pack (e.g. 100, 500, 2000 credits).

Then build the `STRIPE_CREDIT_PACKS` value as `priceId:credits` pairs, comma-separated:
```
price_1AbcOneHundred:100,price_2DefFiveHundred:500
```
(left = Stripe Price ID, right = credits the buyer receives)

## 4. Create the webhook
- Developers → Webhooks → **+ Add endpoint**.
- Endpoint URL:
  `https://social-automation-production-209c.up.railway.app/api/billing/webhook`
- Events to send: select **checkout.session.completed**.
- Add endpoint → copy the **Signing secret** (`whsec_…`) → this is `STRIPE_WEBHOOK_SECRET`.

## 5. Add the variables in Railway
Railway → your service → **Variables** → add:
| Variable | Value |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_…` (live later) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` |
| `STRIPE_CREDIT_PACKS` | `price_xxx:100,price_yyy:500` |
| `BILLING_SUCCESS_URL` | `https://social-automation-production-209c.up.railway.app/#billing?ok=1` |
| `BILLING_CANCEL_URL` | `https://social-automation-production-209c.up.railway.app/#billing?cancel=1` |

Railway redeploys automatically on save.

## 6. Test it
- Open the app → **Billing** → the packs now appear with **Buy** buttons.
- Click Buy → Stripe Checkout → pay with the test card:
  `4242 4242 4242 4242`, any future expiry, any CVC, any ZIP.
- After paying you're redirected back; the webhook credits your account within seconds.

## 7. Go live
- Flip Stripe to **Live mode**, redo steps 2–4 with **live** key / **live** Price IDs / a
  **live** webhook endpoint (live has a different signing secret), and update the three
  `STRIPE_*` vars in Railway.
- Complete Stripe's account activation (business + bank details) so payouts work.

## Notes
- Test and Live are fully separate — test keys only work with test Price IDs/webhook, etc.
- Until `STRIPE_SECRET_KEY` is set, Billing simply shows "not switched on yet" — nothing breaks.
- Prices live in Stripe, never in the code — change a pack price anytime in the dashboard.
