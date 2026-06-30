#!/usr/bin/env bash

set -euo pipefail

echo "Running code quality checks..."

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo ""
echo "Ruff lint"
uv run ruff check .

echo ""
echo "Format check"
uv run ruff format --check .

echo ""
echo "Type checking"
uv run mypy .

echo ""
echo "Running tests"
uv run pytest

echo ""
echo "All quality checks passed."
