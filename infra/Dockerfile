# Applyon backend image: API, Celery workers and the Playwright browser worker share it.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /bin/

WORKDIR /app

# Dependencies first (cached between deploys), from the lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Chromium for auto-submitting applications
RUN playwright install --with-deps chromium

COPY apps/ apps/
COPY packages/ packages/
COPY migrations/ migrations/
COPY alembic.ini .
COPY infra/seed/ infra/seed/

EXPOSE 8000

# Default: API server. Hosts like Render set $PORT.
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
