# ============================================================
# Stage 1: Build
# ============================================================
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml ./packages/shared/
COPY packages/proto-generated/pyproject.toml ./packages/proto-generated/
COPY services/identity-service/pyproject.toml ./services/identity-service/
COPY services/catalog-service/pyproject.toml ./services/catalog-service/
COPY services/scheduling-service/pyproject.toml ./services/scheduling-service/
COPY services/booking-service/pyproject.toml ./services/booking-service/
COPY services/payment-service/pyproject.toml ./services/payment-service/
COPY services/review-service/pyproject.toml ./services/review-service/
COPY services/notification-service/pyproject.toml ./services/notification-service/
COPY services/analytics-service/pyproject.toml ./services/analytics-service/
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
COPY packages/proto-generated/src ./packages/proto-generated/src
COPY services/identity-service/src ./services/identity-service/src
COPY services/catalog-service/src ./services/catalog-service/src
COPY services/scheduling-service/src ./services/scheduling-service/src
COPY services/booking-service/src ./services/booking-service/src
COPY services/payment-service/src ./services/payment-service/src
COPY services/review-service/src ./services/review-service/src
COPY services/notification-service/src ./services/notification-service/src
COPY services/analytics-service/src ./services/analytics-service/src
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
COPY --from=builder /app/services /app/services

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/graphql-api/src:/app/services/identity-service/src:/app/services/catalog-service/src:/app/services/scheduling-service/src:/app/services/booking-service/src:/app/services/payment-service/src:/app/services/review-service/src:/app/services/notification-service/src:/app/services/analytics-service/src:/app/packages/shared/src" \
    PYTHONUNBUFFERED=1

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:4000/health || exit 1

CMD ["uv", "run", "--package", "graphql-api", "uvicorn", \
     "graphql_api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "4000"]
