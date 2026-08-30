# RelayOps, as one container.
#
# The console is compiled in the first stage and copied next to the Python
# package, where the application factory finds and serves it. One image, one
# process, one thing to deploy — the cheapest shape that still runs the real
# API against real PostgreSQL.

# ---- Stage 1: compile the console -------------------------------------------
FROM node:22-alpine AS console

WORKDIR /console
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the application ------------------------------------------------
FROM python:3.13-slim AS app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies resolve from the lockfile before the source is copied, so a code
# change does not invalidate the dependency layer.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --frozen --no-dev

COPY --from=console /console/dist ./console
COPY backend/migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH" \
    CONSOLE_DIST=/app/console

# Gunicorn, not the Flask dev server: the dev server is single-threaded and
# explicitly not for production use. The bind port follows $PORT so the same
# image runs on Fly (PORT=8080 in fly.toml) and on Render (PORT=10000).
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 60 --access-logfile - relayops.wsgi:application"]
