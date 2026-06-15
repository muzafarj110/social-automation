# Autopilot — Product Summary (for audit)

_Prepared: 15 June 2026. Status: launched (v1), production-deployed._

## 1. Overview & mission
Autopilot is a subscription SaaS that acts as an **AI marketing department** for
individuals, creators, and small businesses. It plans, writes, schedules, and publishes
on-brand social content across major platforms, engages with audiences, captures leads,
and learns from performance — automating work that would otherwise require a marketing team.

**Architectural principle:** all AI/generation runs on a separate **AI Models Hub**; the
application only **orchestrates** (calls Hub models), **acts** (publishes via a posting
provider), and **manages** (storage, scheduling, quality checks, analytics, billing). The
application contains no proprietary AI models itself.

## 2. Core features
- **Autopilot campaigns** — set topics/goal, cadence and platforms once; AI generates a
  batch, tailors content per platform, optionally QA-polishes, and schedules it.
- **Quick post** — single AI-generated post with optional infographic and quality check.
- **Multi-platform publishing** — 15 platforms (LinkedIn, X, Instagram, Facebook, TikTok,
  YouTube, Pinterest, Reddit, Bluesky, Threads, Google Business, Telegram, Snapchat,
  WhatsApp, Discord) via a third-party posting provider.
- **Content model** — LinkedIn is AI-written; other platforms post the user's own content,
  AI-optimised for SEO/format/hashtags.
- **Approval inbox** — AI-drafted replies the user approves (compliant auto-reply limited to
  company-page comments).
- **Lead-gen / CRM-lite** — capture leads, pipeline status, AI-drafted outreach.
- **Cross-channel content calendar** and **Posts** management (draft/schedule/publish).
- **Analytics** — reach/engagement aggregated across connected accounts, plus a learning
  loop that biases future content toward what performed.
- **Brand voice / Profile tools**, **Admin dashboard** (operator-only user/plan management).
- **Safety controls** — approve-first default, global pause-automation switch, human-in-the-loop.

## 3. Architecture
- **Frontend:** React (Vite) single-page app; responsive (desktop + mobile drawer).
- **Backend:** Python FastAPI, async SQLAlchemy 2.0, Alembic migrations.
- **Database:** PostgreSQL (production) / SQLite (local dev).
- **Hosting:** Railway (single-service Docker; runs DB migrations on deploy).
- **External services:** AI Models Hub (content generation), Zernio (social posting/OAuth
  connections), Stripe (payments), Resend (transactional email).

## 4. Security & data handling
- **Authentication:** email + password; passwords hashed with bcrypt; JWT bearer sessions.
- **Password reset:** email link; tokens are single-use, time-limited (1h), stored only as
  SHA-256 hashes; request endpoint is enumeration-safe (identical response for any email).
- **Secrets at rest:** per-user third-party API keys encrypted with Fernet (key derived from
  the server secret). Card data is never handled by the app — checkout is hosted by Stripe.
- **Multi-tenant isolation:** every record is owner-scoped; verified by automated tests that a
  user cannot read or act on another user's accounts, posts, campaigns, leads, or billing.
- **White-label connections:** one app-level posting key with a per-customer "profile";
  account listing and analytics are profile-scoped and **fail-closed** (if scope can't be
  established, nothing is returned) — verified by test.
- **Admin gating:** admin-only endpoints restricted to a configured admin email; verified
  (non-admin receives 403).
- **Error handling:** upstream provider errors are mapped to friendly messages; raw provider
  details (org IDs, billing URLs, tokens) are never exposed to end users.
- **Vendor abstraction:** provider names are hidden from customers ("white-label"); a provider
  interface allows swapping the posting backend.

## 5. Billing
- **Model:** usage-based credits. AI actions consume credits; new accounts receive a free
  grant; admins are unlimited.
- **Payments:** Stripe Checkout (hosted) for one-time credit packs; a signed Stripe webhook
  grants credits on `checkout.session.completed`. Prices/packs are defined in Stripe (not in
  code) via environment configuration.

## 6. Quality & verification
- ~64 automated tests (unit + ASGI integration), covering auth, multi-tenant isolation,
  campaigns, billing/credits, password reset, white-label isolation, and platform logic.
- **Live verification (production):** AI generation, credit metering, billing checkout,
  password-reset email delivery, and an end-to-end social publish (a real post published to
  LinkedIn) have all been confirmed working.

## 7. Operational status
- **Live** in production. Core flows verified end-to-end.
- **Payments currently in Stripe TEST mode** (live keys to be enabled before charging real
  customers).
- Single-region, single-service deployment; in-process scheduler for recurring campaigns.

## 8. Known limitations / roadmap (disclosed for completeness)
- Dependency on the external posting provider (Zernio) and AI Hub; mitigated by a provider
  abstraction and per-customer isolation, but a third-party dependency remains.
- Infographics are saved/viewable but not yet rendered into the published post image (planned
  via a Hub image step).
- Not yet built: email marketing campaigns, SEO/long-form content, paid ads, competitive-
  intelligence feed, and formal attribution/A-B testing.
- No formal third-party security audit or penetration test has been performed yet.
