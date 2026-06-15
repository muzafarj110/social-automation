# Autopilot — Mission, Status & Roadmap

_Living document. Last updated 2026-06-13._

## Mission
Replace an entire **marketing department** for any customer — individual, creator,
startup, or company — by automating marketing across **all** social platforms with AI.

**Architecture rule:** all AI lives on the **AI Models Hub**. The app only
**orchestrates** (calls Hub models), **acts** (posts via Zernio), and **manages**
(store, schedule, QA, analytics). It never builds AI itself. Ban-safe, multi-tenant,
subscription-based, admin-controlled feature gating.

## Goal
A non-technical user signs up, connects accounts, and gets on-brand content created,
optimized, scheduled, posted, and improved from results — hands-off, but always under
their control.

## What the product does today ✅
- Multi-tenant isolation (tested), per-user encrypted keys, plan entitlements
  (free/pro/business) + admin dashboard. No cross-tenant or owner-account leaks.
- Profile onboarding + guided first-run wizard.
- Content model: **LinkedIn is AI-written**; other 14 platforms post the **user's own
  content**, AI-optimized for SEO/hashtags/format/reach.
- Autopilot campaigns: topics/goal, cadence, AI timing, auto QA-polish, infographics,
  multi-platform, approve-first by default.
- Posting via Zernio across 15 platforms; media-required platforms held as drafts.
- Approval inbox (compliant auto-reply for company-page comments).
- Analytics auto-pulled across platforms + closed learning loop; AI insights/viral.
- Safety: global pause-automation kill switch, auto-mode warning, friendly Hub errors.
- Resilience: Hub concurrency cap, usage cache; provider seam to swap Zernio.
- ~58 passing tests, deployed on Railway.

## Missing — roadmap (priority order)
1. **Background scheduler/worker** — auto-run recurring campaigns (today mostly manual
   "Run now"). _Without this, "autopilot" isn't automatic._  ← NEXT
2. **Billing/payments (Stripe)** — plans gate features but there's no checkout; can't
   collect subscriptions yet. _Without this, no revenue._
3. **Image/video generation** so media-first platforms (IG, TikTok, YouTube, Pinterest,
   Snapchat) can auto-post instead of staying drafts.
4. **Real SEO/keyword agent on the Hub** (today approximated by content_optimizer). _Hub build._
5. **OAuth connect, verified live** + reduce the Zernio API-key paste (needs Zernio
   delegated auth).
6. **"Whole department" breadth:** email marketing, paid ads, website/SEO, cross-channel
   calendar, competitor monitoring, lead-gen/CRM. _Largest gap vs. mission._
7. **Strategic (not code):** niche positioning; read Zernio's ToS (audit kill-criteria).

## Build plan: Email marketing (scoped, not yet built)
The first dependency-heavy department function. Needs one new integration + one Hub model.

**What it takes**
1. **Sending provider** — Resend (simplest) or SendGrid. Store an API key per user
   (encrypted, like the others) or one app-level key. ~1 client wrapper.
2. **Hub model** — an "email copy" agent on the Hub (subject + body from a brief).
   _Doesn't exist yet — you'd build it; for now `content_optimizer`/`content_strategy`
   could approximate._
3. **App pieces** — `Contact`/list model (reuse `leads`), a `Campaign`-like
   `EmailCampaign` (subject, body, audience filter, schedule), a sender service,
   and credit metering (1 credit per send or per N recipients).
4. **Compliance** — unsubscribe link + suppression list (legal requirement; CAN-SPAM/GDPR).
5. **UI** — compose screen + recipient picker from Leads + send/schedule.

**Effort:** ~1–2 focused builds. **Blocker:** pick a provider + decide if you build
the Hub email model. **Risk:** deliverability/compliance — start with low volume + a
verified sending domain.

## Recently shipped
- Hands-off scheduler (campaigns auto-run on creation).
- Usage-based billing (credits + Stripe checkout/webhook, guarded).
- Cross-channel calendar (all platforms, by day).
- Lead-gen / CRM-lite (capture + AI-drafted outreach).

## Becoming a full marketing department — service build sequence
Order by revenue impact; each row notes the Hub (AI model) vs app (orchestration) split.

1. **Infographic → image in posts** (in progress). Hub: render infographic to a hosted
   PNG + return `image_url`. App: attach as post media → publishes inline. Also unblocks
   image-first platforms.
2. **Email & lifecycle.** Hub: email-copy model (subject + body from a brief). App: contacts
   (reuse leads), email campaigns, Resend sender (already wired), nurture sequences,
   unsubscribe/suppression. _Highest near-term revenue lever._
3. **SEO content (blog/long-form).** Hub: SEO/keyword agent + long-form writer. App: article
   editor, keyword targets, export/publish to site/CMS.
4. **AI Opportunities feed (competitive & market intelligence).** Hub: trend/competitor-watch
   agent. App: a data source to monitor + a feed that turns signals into one-click drafts.
   _Biggest differentiator (proactive/agentic) — mocked for review._
5. **Paid ads.** Needs Meta/Google/LinkedIn Ads API access. App: campaign setup + budget
   pacing; Hub: ad-copy + audience suggestions. Heaviest + most platform-risk; do last.

Cross-cutting moat work (do alongside): make the **learning loop visible** ("posts +32% since
month 1"), and add **outcome reporting** (content → leads → pipeline) so value is provable.

## Known risks (from audits)
- Dependency on Zernio for publishing (mitigated by provider seam; read their ToS).
- Commodity/moat — differentiate via niche + the per-customer learning loop.
- Platform-ban risk — approve-by-default, official APIs only, pause switch.
