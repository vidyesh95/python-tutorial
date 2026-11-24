# syntax=docker/dockerfile:1
# Build from the REPOSITORY ROOT so pyproject.toml and uv.lock are in the context:
#   docker build -f t04_fastapi_backend/docker/Dockerfile -t fastapi-lesson .

# ---- Stage 1: builder (has uv and build tools; discarded afterwards) ----
FROM python:3.15-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copy ONLY the dependency manifests first so this layer is cached until they change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-default-groups --group backend

# ---- Stage 2: runtime (small, no uv, no compilers) ----
FROM python:3.15-slim AS runtime

# Unprivileged user: a compromised process cannot write to the image or run as root.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app t04_fastapi_backend ./t04_fastapi_backend

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WEB_CONCURRENCY=2

USER app
EXPOSE 8000

# slim images have no curl, so use the interpreter we already ship.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

# Exec form (JSON array) so uvicorn is PID 1 and receives SIGTERM for graceful shutdown.
CMD ["uvicorn", "t04_fastapi_backend.m_18_dockerizing_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
