#!/bin/sh
set -e
echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete. Starting application..."
exec "$@"
