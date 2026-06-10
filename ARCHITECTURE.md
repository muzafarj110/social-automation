# LinkedIn Autopilot — System Architecture

**Project:** LinkedIn Autopilot SaaS
**Status:** Architecture plan (pre-build)
**Last updated:** 2026-06-08

A subscription SaaS that automates LinkedIn growth for users. It generates content with the **AI Models Hub** (existing, never rebuilt), publishes and reads analytics through **Zernio** (LinkedIn's official-API layer, already connected), and runs a **hybrid automation engine** — some actions fully automatic (scheduled posts), others AI-drafted for one-click human approval (comments, DMs, profile edits).

---

## 1. Locked decisions

| Area | Decision |
|---|---|
| Codebase | Separate repo from AI Models Hub |
| LinkedIn access | Zernio (official API, already set up) |
| AI layer | Call AI Models Hub's existing endpoints — never build new AI |
| Business model | Subscription SaaS, **manual provisioning for now** (billing added later) |
| Automation | Hybrid: auto for posts, draft-and-approve for comments/DMs/profile |
| Backend | Python FastAPI |
| Frontend | React + Vite |
| Database / host | Railway + Postgres (+ Redis) |
| Auth | Own JWT auth in FastAPI |

---

## 2. The three planes

The system is small because two of its three planes already exist. We only build the middle one.

```
┌──────────────────────────────────────────────────────────────────┐
│  CONTENT BRAIN  (exists)         │  ACTION LAYER  (exists)         │
│  AI Models Hub API               │  Zernio API                     │
│  /api/linkedin-text-post         │  posts · scheduling             │
│  /api/linkedin-post-series       │  analytics                      │
│  /api/linkedin-comment-writer    │  company-page comments          │
│  /api/linkedin-dm-writer         │                                 │
│  /api/linkedin-outreach-campaign │  (DMs / profile NOT in any      │
│  /api/linkedin-profile-optimizer │   official API → draft+approve) │
│  /api/linkedin-headline-variants │                                 │
│  /api/linkedin-engagement-strategy                                 │
└───────────────┬──────────────────────────────┬───────────────────┘
                │                                │
        ┌───────▼────────────────────────────────▼─────────┐
        │   ORCHESTRATOR  (what we build — FastAPI)         │
        │   ───────────────────────────────────────────    │
        │   Auth/JWT · Users · Subscriptions (manual)       │
        │   Pipelines (chain Hub models)                    │
        │   Scheduler + Worker (Redis/RQ)                   │
        │   Approval Inbox (draft→human→send)               │
        │   Zernio client · Hub client                      │
        │   Postgres (state)                                │
        └───────────────────────┬───────────────────────────┘
                                 │ REST + JWT
                    ┌────────────▼────────────┐
                    │  FRONTEND (React/Vite)   │
                    │  Dashboard · Calendar    │
                    │  Approval Inbox · Profile│
                    │  Analytics · Settings    │
                    └──────────────────────────┘
```

---

## 3. Component breakdown

### 3.1 FastAPI backend (the orchestrator)
The only substantial new code. Responsibilities:

- **Auth** — registration, login, JWT issue/verify, password hashing (bcrypt/argon2), role/plan gating.
- **Account management** — link a user to their Zernio-connected LinkedIn account(s); store the Zernio `accountId` per user.
- **Pipelines** — chain Hub model calls into useful outputs (hook → body → hashtags; strategy → 30-day series). Pure orchestration logic, no AI.
- **Scheduler** — turn approved/auto content into time-based jobs.
- **Worker** — execute due jobs (call Zernio to publish; refresh analytics). Redis-backed (RQ to start; Celery if it grows).
- **Approval inbox** — store AI drafts (comments/DMs/profile rewrites) in `pending` state; expose approve/edit/reject; on approve, perform the compliant action (Zernio company comment) or mark "ready to send" for actions the API can't do.
- **Clients** — thin `HubClient` and `ZernioClient` wrappers (httpx), with retries and error mapping.

Suggested internal layout:

```
backend/
  app/
    main.py
    core/        config, security (JWT), db session
    models/      SQLAlchemy ORM
    schemas/     Pydantic request/response
    api/         routers: auth, accounts, content, schedule, inbox, profile, analytics
    services/    pipelines, scheduler, approval engine
    clients/     hub_client.py, zernio_client.py
    workers/     job definitions, worker entrypoint
    db/          migrations (Alembic)
  tests/
```

### 3.2 React + Vite frontend
Mostly CRUD + queues over the backend API:

- **Dashboard** — account health, upcoming posts, pending approvals count, headline metrics.
- **Content Calendar** — generate, schedule, edit, drag-to-reschedule posts.
- **Approval Inbox** — review AI-drafted comments/DMs/profile changes; edit; approve/reject.
- **Profile Studio** — run optimizer + headline variants; show before/after diff; copy/apply.
- **Analytics** — Zernio metrics + Hub's engagement-strategy interpretation.
- **Settings** — connected account, plan/subscription status, preferences (tone, cadence, topics).

**Theme:** reuses the AI Models Hub palette exactly (navy `#121358`, blue `#232F72`, teal accent `#36ADA3`, light `#f0f4ff`, hero gradient `135deg navy→blue`), Segoe UI font, 8px radius. Full tokens + Tailwind config in `THEME.md`.

### 3.3 Postgres
Source of truth for users, accounts, content, schedule, approvals, analytics snapshots. (Schema in §5.)

### 3.4 Redis + worker
Job queue and scheduled execution. Also rate-limit buffering so we never hammer Zernio or the Hub.

---

## 4. How the planes connect

### 4.1 AI Models Hub (content)
- Called server-side only (never expose Hub keys to the browser).
- One `HubClient` with a method per endpoint; standard auth header (Bearer key, confirm exact shape).
- Outputs are **content**, never actions — the Hub never touches LinkedIn.
- Mapping of endpoints to features in §6.

### 4.2 Zernio (LinkedIn actions)
- One `ZernioClient` wrapping the REST API (`https://zernio.com/api/v1`).
- Used for: **create/schedule posts**, **analytics**, **company-page comments** (list/reply/delete).
- **Cannot do** (LinkedIn restriction, not Zernio's): personal-profile comments on others' posts, DMs/InMail, connection requests, profile field edits. These become **draft → human-sends** items in the inbox.
- Subscribe to Zernio `account.disconnected` webhook to catch expired tokens and prompt reconnect.

### 4.3 The hybrid rule (single source of truth)

| Action | Path | Auto or Approve |
|---|---|---|
| Scheduled feed post (text/image/carousel/video) | Hub → Zernio | **Auto** |
| Company-page comment reply | Hub → Zernio | Approve (configurable to auto) |
| Comment on someone else's post | Hub draft → inbox → user sends | **Approve (manual send)** |
| DM / outreach sequence | Hub draft → inbox → user sends | **Approve (manual send)** |
| Profile headline/about rewrite | Hub draft → inbox → user applies | **Approve (manual apply)** |
| Analytics + strategy | Zernio → Hub → dashboard | Auto (read-only) |

This table is the contract the whole app is built around: if an action is reachable through Zernio's official API it can be automated; if not, it is drafted and the human performs the final click. This keeps the product compliant and ban-safe by default.

---

## 5. Data model (Postgres)

```
users
  id, email (unique), password_hash, full_name,
  plan ('free'|'pro'), status ('active'|'suspended'),
  created_at, updated_at

linkedin_accounts
  id, user_id → users,
  zernio_account_id, account_type ('personal'|'organization'),
  display_name, avatar_url, connected_at, last_synced_at,
  status ('connected'|'disconnected')

content_items                      -- generated posts
  id, user_id, account_id,
  source_pipeline ('text-post'|'post-series'|...),
  body, media (jsonb), hashtags (jsonb),
  status ('draft'|'scheduled'|'published'|'failed'),
  zernio_post_id, created_at

schedule
  id, content_item_id → content_items,
  run_at (timestamptz), status ('pending'|'running'|'done'|'failed'),
  attempts, last_error

approvals                          -- the human-in-the-loop queue
  id, user_id, account_id,
  kind ('comment'|'dm'|'profile'|'outreach'),
  ai_payload (jsonb),              -- the Hub draft
  context (jsonb),                 -- target post/person, etc.
  status ('pending'|'approved'|'rejected'|'sent'),
  executed_via ('zernio'|'manual'), created_at, resolved_at

profile_snapshots
  id, account_id, headline, about, optimized (jsonb),
  applied (bool), created_at

analytics_snapshots
  id, account_id, period_start, period_end,
  metrics (jsonb), interpretation (text),  -- Hub strategy output
  created_at

subscriptions                      -- manual now, billing-ready later
  id, user_id, plan, status, provisioned_by,
  current_period_end, notes, created_at
```

Encrypt any sensitive tokens at rest. Zernio holds the LinkedIn OAuth tokens (not us), which is a security win — we only store the `zernio_account_id` reference.

---

## 6. Hub endpoint → feature mapping

| Hub endpoint | Drives feature | Output path |
|---|---|---|
| `/api/linkedin-text-post` | Single post generation | → schedule → Zernio (auto) |
| `/api/linkedin-post-series` | Content calendar (e.g. 30-day) | → bulk drafts → calendar → Zernio |
| `/api/linkedin-comment-writer` | Comment drafts | → approval inbox |
| `/api/linkedin-dm-writer` | Single DM draft | → approval inbox (manual send) |
| `/api/linkedin-outreach-campaign` | Multi-step DM sequence | → approval inbox per step (manual send) |
| `/api/linkedin-profile-optimizer` | Profile rewrite | → Profile Studio diff (manual apply) |
| `/api/linkedin-headline-variants` | Headline A/B options | → Profile Studio (manual apply) |
| `/api/linkedin-engagement-strategy` | Strategy + analytics read | → dashboard + drives what to generate |

---

## 7. Core API surface (FastAPI)

```
POST   /auth/register
POST   /auth/login
GET    /auth/me

GET    /accounts                       list linked LinkedIn accounts
POST   /accounts/link                  attach a Zernio accountId
DELETE /accounts/{id}

POST   /content/generate               body: {pipeline, params} → Hub → draft
GET    /content                        list drafts/scheduled/published
PATCH  /content/{id}                   edit body/media
POST   /content/{id}/schedule          {run_at} → schedule + worker
POST   /content/{id}/publish-now       → Zernio immediately
DELETE /content/{id}

GET    /schedule                       calendar view
PATCH  /schedule/{id}                  reschedule

GET    /inbox                          pending approvals
POST   /inbox/generate                 {kind, context} → Hub draft → queue
POST   /inbox/{id}/approve             execute (Zernio) or mark ready-to-send
POST   /inbox/{id}/reject
PATCH  /inbox/{id}                     edit draft before approving

POST   /profile/optimize               → Hub → snapshot/diff
GET    /profile/snapshots

GET    /analytics                      Zernio metrics + Hub interpretation

# admin (manual provisioning)
POST   /admin/users/{id}/provision     set plan/status by hand
```

---

## 8. Build roadmap (feature by feature)

Each phase is independently shippable. Recommended order:

**Phase 0 — Skeleton.** FastAPI app, Postgres + Alembic, Railway deploy, health check, `.env` config, `HubClient` + `ZernioClient` stubs with one real call each (smoke test both integrations end-to-end).

**Phase 1 — Auth + accounts.** JWT register/login, link a Zernio account, basic React shell + login. *Milestone: a user can log in and see their connected LinkedIn account.*

**Phase 2 — Post generation + publish.** `/content/generate` via `/api/linkedin-text-post`, review, **publish-now** via Zernio. *Milestone: AI post goes live on LinkedIn from our UI.*

**Phase 3 — Scheduling.** Redis + worker, calendar UI, schedule + auto-publish. Add `/api/linkedin-post-series` for bulk calendar fill. *Milestone: set-and-forget posting.*

**Phase 4 — Approval inbox.** Comments + DMs drafted by Hub, review/edit/approve; company-page comments execute via Zernio, others mark ready-to-send. *Milestone: the "hybrid" promise is real.*

**Phase 5 — Profile Studio.** Optimizer + headline variants, before/after diff, copy/apply.

**Phase 6 — Analytics + strategy loop.** Zernio metrics → `/api/linkedin-engagement-strategy` interpretation → recommendations that feed back into generation.

**Phase 7 — Billing.** Swap manual provisioning for Stripe/Paddle when ready (data model already supports it).

---

## 9. Security & compliance notes

- **No LinkedIn credentials touch our servers** — Zernio holds OAuth tokens. We store only references. Big liability reduction.
- **Hub keys are server-side only**, never shipped to the browser.
- **Compliant-by-default:** anything not in LinkedIn's official API is draft-and-human-send, so we don't put user accounts at ban risk. (If a browser-automation "power" tier is ever added, it must be opt-in, rate-limited, warned, and isolated — explicitly out of scope for v1.)
- JWT short expiry + refresh; bcrypt/argon2 password hashing; per-user rate limits on generation to control Hub usage/cost.
- Honor LinkedIn content rules Zernio surfaces: duplicate-content 422s, link suppression (use `firstComment` for URLs), media-type mixing limits.

---

## 10. Open questions to confirm before/while building

1. **Hub auth + payload shape** — exact header and request/response JSON for one endpoint (e.g. `/api/linkedin-text-post`). Needed to write `HubClient`.
2. **Zernio API key location** — confirm it lives in backend env only.
3. **Account linking UX** — does each SaaS user run their own Zernio connect flow, or do we manage Zernio centrally and map accounts? (Affects `accounts/link`.)
4. **Plan limits** — what does free vs pro gate (posts/day, accounts, inbox volume)?
5. **Media hosting** — where do generated images/carousels live so Zernio can fetch public URLs (Railway volume? S3? Supabase storage)?

---

*Next step: once §10.1 (one Hub request/response example) is confirmed, build Phase 0 — the skeleton with live smoke tests against both the Hub and Zernio.*
