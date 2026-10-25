# ============================================================
# Stage 1: Build - установка зависимостей
# ============================================================
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml ./packages/shared/
COPY services/review-service/pyproject.toml ./services/review-service/

RUN mkdir -p packages/shared/src/shared \
    && mkdir -p services/review-service/src/review_service \
    && touch packages/shared/src/shared/__init__.py \
    && touch services/review-service/src/review_service/__init__.py

RUN uv sync \
    --package review-service \
    --frozen \
    --no-dev \
    --no-install-workspace

COPY packages/shared/src ./packages/shared/src
COPY services/review-service/src ./services/review-service/src
COPY services/review-service/migrations ./services/review-service/migrations

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
COPY --from=builder /app/services/review-service /app/services/review-service

COPY services/review-service/docker/entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["uv", "run", "--package", "review-service", "uvicorn", "review_service.main:app", "--host", "0.0.0.0", "--port", "8006"]
