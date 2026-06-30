#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Auto-fixing code..."
uv run ruff check . --fix
uv run ruff format .
echo "Done."
