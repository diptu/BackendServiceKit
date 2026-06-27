#!/usr/bin/env bash

set -euo pipefail

echo "Auto-fixing code..."

uv run ruff check . --fix
uv run ruff format .

echo "Formatting completed."
