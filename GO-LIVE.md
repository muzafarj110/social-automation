# Go-Live — launch this week

The product is feature-complete for v1 (multi-platform autopilot, white-label connections,
usage-based billing, password reset, redesigned + mobile, ~64 tests, deployed). This week is
business setup + proof, not building.

## The one true blocker
- [ ] **Live smoke test** — connect a real LinkedIn/X account, create a campaign, publish ONE
      real post end-to-end. If this works, the core is proven. Everything else is setup.

## Required to charge / operate (do this week)
- [ ] **Stripe live** — switch to live secret key; create credit-pack **Price IDs**; set
      `STRIPE_CREDIT_PACKS`, `STRIPE_WEBHOOK_SECRET`, `BILLING_SUCCESS_URL`, `BILLING_CANCEL_URL`;
      point a Stripe webhook at `/api/billing/webhook`. Decide pack prices.
- [ ] **Resend domain verified** — so password-reset (and future email) lands, not spam.
- [ ] **Pricing decided** — credit pack sizes + prices; confirm `FREE_CREDITS` trial amount.
- [ ] **Two-tenant isolation spot-check** — second account sees only its own data (we hardened
      this; a 5-min live check before real users arrive).

## Nice-to-have (only if time; not blockers)
- [ ] Custom domain in front of the Railway URL.
- [ ] A simple terms/privacy link.

## Explicitly DEFER to v1.1 (do not block launch)
Infographic-rendered-into-post (Hub image), AI Opportunities feed, email campaigns, SEO content,
paid ads, AI image generation. All roadmapped; none required to launch.

## Dogfood — we are customer #1
Use Autopilot to run its own launch (markets the product AND is live proof):
1. Connect your LinkedIn/X; set brand voice.
2. Create a "Launch week" campaign (topics below), approve-first.
3. Generate → review → schedule the week's posts.
4. Screenshot results for social proof ("we replaced our own marketing dept with this").

Launch content is drafted in `launch-content.md`.

## Go / no-go
GREEN to launch when the live smoke test passes and Stripe live + Resend domain are set.
