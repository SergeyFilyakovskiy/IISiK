FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml ./packages/shared/
COPY packages/proto-generated/pyproject.toml ./packages/proto-generated/
COPY services/graphql-api/pyproject.toml ./services/graphql-api/

RUN mkdir -p packages/shared/src/shared services/graphql-api/src/graphql_api \
    && touch packages/shared/src/shared/__init__.py services/graphql-api/src/graphql_api/__init__.py

RUN uv sync --package graphql-api --frozen --no-dev --no-install-workspace

COPY packages/shared/src ./packages/shared/src
COPY packages/proto-generated/src ./packages/proto-generated/src
COPY services/graphql-api/src ./services/graphql-api/src

FROM python:3.14-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/services/graphql-api /app/services/graphql-api

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/graphql-api/src:/app/packages/shared/src:/app/packages/proto-generated/src" \
    PYTHONUNBUFFERED=1

EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:4000/health || exit 1
CMD ["uv", "run", "--package", "graphql-api", "uvicorn", "graphql_api.main:app", "--host", "0.0.0.0", "--port", "4000"]
