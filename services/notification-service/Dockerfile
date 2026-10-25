# ============================================================
# Stage 1: Build
# ============================================================
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml ./packages/shared/
COPY services/notification-service/pyproject.toml ./services/notification-service/

RUN mkdir -p packages/shared/src/shared \
    && mkdir -p services/notification-service/src/notification_service \
    && touch packages/shared/src/shared/__init__.py \
    && touch services/notification-service/src/notification_service/__init__.py

RUN uv sync \
    --package notification-service \
    --frozen \
    --no-dev \
    --no-install-workspace

COPY packages/shared/src ./packages/shared/src
COPY services/notification-service/src ./services/notification-service/src
COPY services/notification-service/alembic.ini ./services/notification-service/alembic.ini
COPY services/notification-service/migrations ./services/notification-service/migrations

# ============================================================
# Stage 2: Runtime
# ============================================================
FROM python:3.14-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        util-linux \
        procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/
COPY --from=builder /app/uv.lock /app/
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/services/notification-service /app/services/notification-service

COPY services/notification-service/docker/entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["uv", "run", "--package", "notification-service", "python", "-m", "notification_service.consumer"]
