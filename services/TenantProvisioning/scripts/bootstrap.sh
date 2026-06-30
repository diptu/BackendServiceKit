#!/usr/bin/env bash

set -euo pipefail

echo "Bootstrapping Tenant Provisioning Service..."

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed."
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
uv sync

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "Creating .env from .env.example"
    cp .env.example .env
fi

mkdir -p logs tmp

if command -v alembic >/dev/null 2>&1; then
    echo "Running migrations..."
    alembic upgrade head || true
fi

echo ""
echo "Tenant Provisioning Service bootstrap completed."
echo ""
echo "Start API server:"
echo "  uv run uvicorn app.main:app --reload --port 8003"
echo ""
echo "Start Celery worker:"
echo "  uv run celery -A app.tasks.worker.celery_app worker --loglevel=info --queues=celery"
