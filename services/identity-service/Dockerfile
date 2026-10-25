# ============================================================
# Stage 1: Build - установка зависимостей
# ============================================================
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml ./packages/shared/
COPY services/identity-service/pyproject.toml ./services/identity-service/

RUN mkdir -p packages/shared/src/shared \
    && mkdir -p services/identity-service/src/identity_service \
    && touch packages/shared/src/shared/__init__.py \
    && touch services/identity-service/src/identity_service/__init__.py

RUN uv sync \
    --package identity-service \
    --frozen \
    --no-dev \
    --no-install-workspace

COPY packages/shared/src ./packages/shared/src
COPY services/identity-service/src ./services/identity-service/src
COPY services/identity-service/alembic.ini ./services/identity-service/alembic.ini
COPY services/identity-service/migrations ./services/identity-service/migrations

# ============================================================
# Stage 2: Runtime - финальный образ
# ============================================================
FROM python:3.14-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/
COPY --from=builder /app/uv.lock /app/
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/services/identity-service /app/services/identity-service

COPY services/identity-service/docker/entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["uv", "run", "--package", "identity-service", "uvicorn", "identity_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
