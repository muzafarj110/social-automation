# Deploying LinkedIn Autopilot to Railway

One Railway service runs everything: FastAPI serves the API **and** the built
React frontend on a single URL, backed by Railway Postgres. The included
`Dockerfile` builds the frontend and backend together; Railway detects it
automatically. Alembic migrations run on every deploy.

## 1. Push the repo to GitHub

From the project root:

```bash
git add -A
git commit -m "Add Railway deploy config"        # if not already committed
# create an EMPTY repo on github.com first (no README), then:
git remote add origin https://github.com/<you>/linkedin-autopilot.git
git branch -M main
git push -u origin main
```

`.env` is git-ignored, so your secrets are **not** pushed — you'll set them in
Railway instead (step 4).

## 2. Create the Railway project

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**.
2. Pick the repo. Railway finds the `Dockerfile` and starts a build.
3. The first build will succeed but the app won't be healthy yet — it needs a
   database and env vars (next steps). That's expected.

## 3. Add Postgres

In the project: **New** → **Database** → **Add PostgreSQL**. Railway creates a
`Postgres` service and exposes a `DATABASE_URL`.

## 4. Set environment variables

Open the **app service** → **Variables**, and add:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}`  ← reference, links the DB |
| `JWT_SECRET` | a long random string (see below) |
| `HUB_BASE_URL` | `https://ai-marketing-hub-production-fccb.up.railway.app` |
| `HUB_API_KEY` | your Hub key (from local `.env`) |
| `ZERNIO_BASE_URL` | `https://zernio.com/api/v1` |
| `ZERNIO_API_KEY` | your Zernio key (from local `.env`) |

Generate a fresh production `JWT_SECRET` (don't reuse the dev one):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

A ready-to-use one (fine to paste, or generate your own):

```
l28JDiCNqcbRv5bMUZPw8QxmVKquyklwXtRI0Oio0CVcfZwAfztTow9HRdmjI4pRfPnF7eU_-5hbVhtVh3nlZQ
```

Setting variables triggers a redeploy. On boot the container runs
`alembic upgrade head`, creating all tables (`users`, `linkedin_accounts`,
`posts`, `approvals`) in Postgres.

## 5. Get a public URL

App service → **Settings** → **Networking** → **Generate Domain**. Open it: you
should see the login screen. `…/docs` still serves the API docs.

## 6. First use

Register an account → **Accounts** tab → link your Zernio LinkedIn account →
generate/publish posts, or draft and approve actions in the **Inbox**.

---

## How it fits together

- **Build:** `Dockerfile` stage 1 (Node) runs `npm run build` → `frontend/dist`;
  stage 2 (Python) installs `requirements.txt` and copies the built frontend in.
- **Runtime:** `uvicorn app.main:app` on `$PORT`. `app/main.py` serves
  `frontend/dist` on `/` and the API under `/api`, same origin (no CORS needed).
- **DB:** `DATABASE_URL` (`postgresql://…`) is normalized to the async psycopg
  driver by the app and to a sync driver by Alembic — one URL, both work.
- **Migrations:** run automatically via the container `CMD`. To add a table
  later: change the model, `alembic revision --autogenerate -m "…"`, commit,
  push — Railway applies it on deploy.

## Troubleshooting

- **Build fails on `npm`:** the Dockerfile uses `npm install` (not `npm ci`) to
  dodge npm's cross-platform optional-dep bug — keep it that way.
- **App boots but DB errors:** confirm `DATABASE_URL` is the `${{Postgres.…}}`
  reference, not blank.
- **401s after redeploy:** changing `JWT_SECRET` invalidates existing sessions —
  log in again.
