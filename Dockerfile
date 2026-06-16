# LinkedIn Autopilot — single-image deploy (Railway).
# Stage 1 builds the React frontend; stage 2 runs FastAPI, which serves both
# the API and the built frontend on one port.

# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# `npm install` (not `npm ci`): the lockfile is generated on macOS and npm has a
# known bug omitting Linux-only optional deps (rollup/esbuild) under `npm ci`,
# which breaks the Vite build in this Linux image.
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build          # -> /app/frontend/dist

# ---- Stage 2: backend runtime ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
# Built frontend served by FastAPI (see app/main.py FRONTEND_DIST).
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# Startup script: auto-detects legacy databases (created by init_db before
# Alembic was introduced) and stamps them before running upgrade head.
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Railway injects $PORT. The startup script handles migration + server launch.
CMD ["/app/start.sh"]
