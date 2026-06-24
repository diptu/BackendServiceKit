#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
    echo "Usage:"
    echo "./scripts/release.sh v1.0.0"
    exit 1
fi

echo "🚀 Releasing IAM Service ${VERSION}"

cd "$SERVICE_ROOT"

# ---------------------------------------------------------
# Sync latest changes
# ---------------------------------------------------------
git pull

# ---------------------------------------------------------
# Auto-fix formatting and lint issues
# ---------------------------------------------------------
echo ""
echo "🔧 Running auto-fixes..."
"$SCRIPT_DIR/fix.sh"

# ---------------------------------------------------------
# Run quality checks
# ---------------------------------------------------------
echo ""
echo "🔍 Running quality checks..."
"$SCRIPT_DIR/lint.sh"

# ---------------------------------------------------------
# Build container image
# ---------------------------------------------------------
IMAGE_NAME="backendservicekit/iam"

echo ""
echo "🐳 Building Docker image..."

docker build \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:latest" \
    .

# ---------------------------------------------------------
# Success
# ---------------------------------------------------------
echo ""
echo "✅ Release completed successfully"
echo ""
echo "Images created:"
echo "  ${IMAGE_NAME}:${VERSION}"
echo "  ${IMAGE_NAME}:latest"

