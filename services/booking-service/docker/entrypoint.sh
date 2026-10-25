#!/bin/bash
set -e

LOCK_FILE="/tmp/alembic.lock"

run_migrations() {
    if [ "$SKIP_MIGRATIONS" = "true" ]; then
        echo "Skipping migrations (SKIP_MIGRATIONS=true)"
        return 0
    fi

    echo "Acquiring migration lock..."
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "Another instance is running migrations, waiting..."
        flock 200
        echo "Lock acquired, migrations already applied"
        return 0
    fi

    echo "Running Alembic migrations..."
    uv run --package booking-service alembic upgrade head
    echo "Migrations applied successfully"
}

run_migrations

echo "Starting application: $@"
exec "$@"
