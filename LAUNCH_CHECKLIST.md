# Launch checklist — multi-platform + audit fixes

This pass turned the LinkedIn-only build into a multi-platform product and
addressed the audit risks. Below is what's done, what to run, and the two steps
only you can finish (they need live keys / a Hub decision).

## What changed (committed)

- **All 15 platforms.** Twitter/X, Instagram, Facebook, LinkedIn, TikTok, YouTube,
  Pinterest, Reddit, Bluesky, Threads, Google Business, Telegram, Snapchat,
  WhatsApp, Discord. The app is now platform-agnostic; LinkedIn is just one of them.
- **Per-platform AI tailoring.** A campaign targets multiple platforms; each idea
  is rewritten by the Hub to fit each platform's norms, then trimmed to that
  platform's character limit (e.g. 280 for X) and hashtag rules at publish time.
- **Token/rate-limit resilience.** App-wide concurrency cap on Hub calls so a
  burst can't slam the shared budget; per-key 60s cache on the usage endpoint;
  existing 429 backoff retained; friendly "service busy" errors (no raw provider
  details leak).
- **Multi-tenant isolation tests** (`backend/tests/test_isolation.py`) prove a
  user can't see or act on another user's accounts, posts, or campaigns, and that
  admin endpoints reject non-admins.
- **Onboarding barrier lowered.** Generation works on the managed Hub key with no
  setup; a Zernio key is only needed when the user wants to connect/post to real
  accounts (kept per-user — that's the isolation boundary).

## Run before deploy (your venv)

Note: the venv exposes `python3` (not `python`). Do NOT run `alembic` locally —
the local SQLite dev DB is owned by `init_db()` (create_all), not Alembic.
Alembic is for production (Postgres) only, applied automatically on deploy.

```bash
cd backend
source .venv/bin/activate          # your Mac venv
pip install -r requirements.txt    # if needed

# 1. Run the suite (tests use their own throwaway DBs — autopilot.db untouched)
python3 -m pytest tests/ -v

# 2. Add the new columns to your existing local dev DB (preserves data).
#    Mirrors migration 0011. Skip if you just `rm autopilot.db` for a clean slate.
sqlite3 autopilot.db "ALTER TABLE linkedin_accounts ADD COLUMN platform VARCHAR(32) NOT NULL DEFAULT 'linkedin';"
sqlite3 autopilot.db "ALTER TABLE posts ADD COLUMN platform VARCHAR(32) NOT NULL DEFAULT 'linkedin';"
sqlite3 autopilot.db "ALTER TABLE campaigns ADD COLUMN platforms JSON;"
```

Then push (the sandbox can't write git locks, so push from your machine):

```bash
git push
```

On deploy, Railway runs `alembic upgrade head` against Postgres (already stamped
at 0010), applying migration 0011 — so production columns migrate automatically.
You never run alembic by hand locally.

## Two steps only you can finish

1. **Hub capacity (the #1 scaling risk).** The Hub currently runs on a shared
   Groq free tier (100k tokens/day for the whole org). With a few active users
   this caps out daily. Before real launch: move the Hub to a paid/Dev tier, or
   provision a per-customer Hub key, and load-test it. This is a decision on the
   Hub, not the app — the app already prefers per-user keys and degrades
   gracefully when the budget is hit.

2. **Live smoke test with real accounts.** I can't run your live keys from here.
   In the deployed app: set your Zernio key → "Find accounts on Zernio" → link an
   account on 2–3 platforms → create a campaign targeting those platforms →
   "Run now" → confirm one tailored draft per platform appears, then publish one
   to verify it lands.

## Optional next (per the architecture rule)

A dedicated **"repurpose for platform"** model on the Hub would tailor content
better than the current content-optimizer reuse. Build it on the Hub and the app
will call it — flagging it here rather than building AI into the app.
