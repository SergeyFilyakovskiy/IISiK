# ============================================================
# Stage 1: Build
# ============================================================
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml ./packages/shared/
COPY services/graphql-api/pyproject.toml ./services/graphql-api/

RUN mkdir -p packages/shared/src/shared \
    && mkdir -p services/graphql-api/src/graphql_api \
    && touch packages/shared/src/shared/__init__.py \
    && touch services/graphql-api/src/graphql_api/__init__.py

RUN uv sync \
    --package graphql-api \
    --frozen \
    --no-dev \
    --no-install-workspace

COPY packages/shared/src ./packages/shared/src
COPY services/graphql-api/src ./services/graphql-api/src

# ============================================================
# Stage 2: Runtime
# ============================================================
FROM python:3.14-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/
COPY --from=builder /app/uv.lock /app/
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/services/graphql-api /app/services/graphql-api

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:4000/health || exit 1

CMD ["uv", "run", "--package", "graphql-api", "uvicorn", \
     "graphql_api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "4000"]
