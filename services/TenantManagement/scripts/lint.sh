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
uv run mypy --python-executable .venv/bin/python .

echo ""
echo "Pylint — clone detection (R0801)"
uv run pylint app/

echo ""
echo "Running tests"
uv run pytest

if command -v bandit >/dev/null 2>&1; then
    echo ""
    echo "Security scan"
    uv run bandit -r app
fi

echo ""
echo "All quality checks passed."
