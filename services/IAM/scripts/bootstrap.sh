#!/usr/bin/env bash

set -euo pipefail

echo "🚀 Bootstrapping IAM Service..."

# ---------------------------------------------------------
# Verify uv
# ---------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv is not installed."
    echo "Install with:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# ---------------------------------------------------------
# Create virtual environment
# ---------------------------------------------------------
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
fi

# ---------------------------------------------------------
# Activate environment
# ---------------------------------------------------------
source .venv/bin/activate

# ---------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------
echo "📥 Installing dependencies..."
uv sync

# ---------------------------------------------------------
# Create environment file
# ---------------------------------------------------------
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "📝 Creating .env from .env.example"
    cp .env.example .env
fi

# ---------------------------------------------------------
# Create logs directory
# ---------------------------------------------------------
mkdir -p logs

# ---------------------------------------------------------
# Create tmp directory
# ---------------------------------------------------------
mkdir -p tmp

# ---------------------------------------------------------
# Run database migrations (optional)
# ---------------------------------------------------------
if command -v alembic >/dev/null 2>&1; then
    echo "🗄 Running migrations..."
    alembic upgrade head || true
fi

# ---------------------------------------------------------
# Success
# ---------------------------------------------------------
echo ""
echo "✅ IAM Service bootstrap completed."
echo ""
echo "Start server:"
echo "source .venv/bin/activate"
echo "uv run uvicorn main:app --reload"
