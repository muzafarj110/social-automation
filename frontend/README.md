# LinkedIn Autopilot — Frontend

React + Vite UI for the Autopilot backend.

## Run

Make sure the backend is running first (on port 8001):

```
cd ../backend
uvicorn app.main:app --reload --port 8001
```

Then, in this folder:

```
npm install
npm run dev
```

Open http://localhost:5173

The Vite dev server proxies `/api/*` to the backend at `http://127.0.0.1:8001`,
so there are no CORS issues in development. To point at a different backend,
edit the `proxy` target in `vite.config.js`.

## Flow

1. **Register / sign in**
2. **Accounts tab** — (optionally set your Hub key) → "Find accounts on Zernio"
   → Link your LinkedIn account, or link manually with a Zernio account ID
3. **Generate tab** — describe a topic → Generate → edit the post → pick an
   account → Save as draft
4. **Posts tab** — Publish now, or schedule for later; published posts link
   straight to LinkedIn

## Theme

Colors and fonts mirror the AI Models Hub (`../THEME.md`): navy `#121358`,
blue `#232F72`, teal accent `#36ADA3`, hero gradient, Segoe UI.
