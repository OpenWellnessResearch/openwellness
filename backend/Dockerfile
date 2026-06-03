# Multi-stage build for the OpenWellness backend workspace.
# Build context is ./backend. Named targets so the same Dockerfile can
# serve the scheduler later from this context.

# ---- builder: resolve and install deps into /app/.venv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy manifests only first so the dependency layer caches independently
# of source changes. The whole workspace must resolve, so every member's
# pyproject is needed even though only api+core get installed.
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/pyproject.toml
COPY api/pyproject.toml api/pyproject.toml
COPY scheduler/pyproject.toml scheduler/pyproject.toml

# Install external deps of api (and its core dependency) without the
# workspace packages themselves — this layer is cached across source edits.
RUN uv sync --frozen --package openwellness-api --no-install-workspace --no-dev

# Now bring in the source for the packages we actually install.
COPY core/ core/
COPY api/ api/

# Install api + core themselves into the venv.
RUN uv sync --frozen --package openwellness-api --no-dev

# ---- api: lean runtime image ----
FROM python:3.12-slim-bookworm AS api

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/core /app/core
COPY --from=builder --chown=app:app /app/api /app/api

ENV PATH="/app/.venv/bin:$PATH"

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status == 200 else 1)"

CMD ["uvicorn", "openwellness_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# ---- scheduler-builder: resolve scheduler (+core) deps and source ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS scheduler-builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/pyproject.toml
COPY api/pyproject.toml api/pyproject.toml
COPY scheduler/pyproject.toml scheduler/pyproject.toml

# Cache the external dependency layer independently of source changes.
RUN uv sync --frozen --package openwellness-scheduler --no-install-workspace --no-dev

COPY core/ core/
COPY scheduler/ scheduler/

RUN uv sync --frozen --package openwellness-scheduler --no-dev

# ---- scheduler: lean Celery worker runtime ----
FROM python:3.12-slim-bookworm AS scheduler

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=scheduler-builder --chown=app:app /app/.venv /app/.venv
COPY --from=scheduler-builder --chown=app:app /app/core /app/core
COPY --from=scheduler-builder --chown=app:app /app/scheduler /app/scheduler

ENV PATH="/app/.venv/bin:$PATH"

USER app

CMD ["celery", "-A", "openwellness_scheduler", "worker", "-l", "info"]
