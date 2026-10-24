# Multi-entrypoint Dockerfile for Applyon Backend
FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /bin/

WORKDIR /app

# Copy dependency specifications
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system -e .

# Copy application code
COPY apps/ apps/
COPY packages/ packages/
COPY .env.example .env

EXPOSE 8000

# Default entrypoint runs FastAPI API server
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
