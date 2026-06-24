#!/usr/bin/env bash

set -euo pipefail

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
    echo "Usage:"
    echo "./scripts/release.sh v1.0.0"
    exit 1
fi

echo "🚀 Releasing IAM Service ${VERSION}"

# ---------------------------------------------------------
# Verify git repository
# ---------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null

# ---------------------------------------------------------
# Ensure branch is clean
# ---------------------------------------------------------
if [[ -n $(git status --porcelain) ]]; then
    echo "❌ Working tree is not clean."
    exit 1
fi

# ---------------------------------------------------------
# Pull latest changes
# ---------------------------------------------------------
git pull

# ---------------------------------------------------------
# Run quality checks
# ---------------------------------------------------------
echo "🔍 Running quality checks..."
./scripts/lint.sh

# ---------------------------------------------------------
# Build Docker image
# ---------------------------------------------------------
IMAGE_NAME="backend-service-kit/iam"

echo "🐳 Building Docker image..."
docker build -t "${IMAGE_NAME}:${VERSION}" .

# ---------------------------------------------------------
# Tag git release
# ---------------------------------------------------------
echo "🏷 Creating git tag..."
git tag "${VERSION}"

# ---------------------------------------------------------
# Push tag
# ---------------------------------------------------------
git push origin "${VERSION}"

# ---------------------------------------------------------
# Optional container push
# ---------------------------------------------------------
# docker push "${IMAGE_NAME}:${VERSION}"

echo ""
echo "✅ Release completed successfully"
echo ""
echo "Image:"
echo "${IMAGE_NAME}:${VERSION}"

