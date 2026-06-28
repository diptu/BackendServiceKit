#!/usr/bin/env bash
# bootstrap.sh — First-time setup for the TenantManagement service.
#
# Run this once after cloning the repo or setting up a new dev machine:
#
#   bash scripts/bootstrap.sh
#
# Idempotent — safe to re-run on an already-configured environment.

set -euo pipefail

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SERVICE_DIR}"

echo "==> TenantManagement bootstrap"

# 1. Environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "    Created .env from .env.example — update with real credentials."
else
    echo "    .env already exists — skipping."
fi

# 2. Python dependencies
echo "==> Installing dependencies (uv sync)"
uv sync

# 3. Database migrations
echo "==> Applying database migrations (alembic upgrade head)"
uv run alembic upgrade head

echo ""
echo "Bootstrap complete."
echo ""
echo "Start the dev server:"
echo "  uv run uvicorn app.main:app --reload --port 8000"
echo ""
echo "Run quality checks:"
echo "  bash scripts/lint.sh"
echo ""
echo "Seed the database:"
echo "  uv run python scripts/seed.py"
