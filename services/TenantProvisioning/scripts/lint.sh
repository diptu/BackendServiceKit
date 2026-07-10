#!/usr/bin/env bash

set -euo pipefail

echo "🔍 Running code quality checks..."

# ---------------------------------------------------------
# Activate virtual environment
# ---------------------------------------------------------
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# ---------------------------------------------------------
# Ruff Lint
# ---------------------------------------------------------
echo ""
echo "▶ Ruff lint"
uv run ruff check .

# ---------------------------------------------------------
# Ruff Format Check
# ---------------------------------------------------------
echo ""
echo "▶ Format check"
uv run ruff format --check .

# ---------------------------------------------------------
# MyPy
# ---------------------------------------------------------
echo ""
echo "▶ Type checking"
uv run mypy .

# ---------------------------------------------------------
# Unit + Integration Tests
# ---------------------------------------------------------
echo ""
echo "▶ Running tests"
uv run pytest

# ---------------------------------------------------------
# Optional Security Scan
# ---------------------------------------------------------
if command -v bandit >/dev/null 2>&1; then
    echo ""
    echo "▶ Security scan"
    uv run bandit -r app
fi

echo ""
echo "✅ All quality checks passed."

