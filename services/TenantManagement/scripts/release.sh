#!/usr/bin/env bash
# release.sh — Validate quality, build a versioned Docker image, and tag the commit.
#
# The quality gate (lint.sh) is MANDATORY and always runs first.
# The release is aborted if any check fails — no Docker build, no git tag.
#
# Usage:
#   bash scripts/release.sh                        # quality gate + build + tag (no push)
#   bash scripts/release.sh --push                 # also push image to registry
#   bash scripts/release.sh --dry-run              # quality gate + plan only, no side effects
#   bash scripts/release.sh --registry my.gcr.io   # override registry host
#   bash scripts/release.sh --repo org/repo        # override GitHub repo (image prefix)
#   bash scripts/release.sh --skip-branch-check    # allow release from non-main branch

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="${SERVICE_DIR}/scripts"

# Canonical service identifier — lowercase, matches CD pipeline convention.
SERVICE_NAME="tenantmanagement"

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

if [ -t 1 ]; then
    C_RESET="\033[0m"; C_BOLD="\033[1m"; C_DIM="\033[2m"
    C_GREEN="\033[32m"; C_YELLOW="\033[33m"; C_BLUE="\033[34m"
    C_CYAN="\033[36m"; C_RED="\033[31m"
else
    C_RESET=""; C_BOLD=""; C_DIM=""
    C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_CYAN=""; C_RED=""
fi

_info()    { echo -e "  ${C_CYAN}»${C_RESET}  $*"; }
_ok()      { echo -e "  ${C_GREEN}✓${C_RESET}  $*"; }
_warn()    { echo -e "  ${C_YELLOW}⚠${C_RESET}  $*"; }
_section() { echo -e "\n${C_BOLD}${C_BLUE}▸ $*${C_RESET}"; }
_die()     { echo -e "\n${C_RED}${C_BOLD}ERROR:${C_RESET} $*\n" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

DRY_RUN=false
PUSH=false
REGISTRY="ghcr.io"
REPO=""
SKIP_BRANCH_CHECK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            ;;
        --push)
            PUSH=true
            ;;
        --registry)
            [[ $# -ge 2 ]] || _die "--registry requires an argument."
            REGISTRY="$2"; shift
            ;;
        --repo)
            [[ $# -ge 2 ]] || _die "--repo requires an argument."
            REPO="$2"; shift
            ;;
        --skip-branch-check)
            SKIP_BRANCH_CHECK=true
            ;;
        -h|--help)
            echo "Usage: bash scripts/release.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run              Quality gate only — no git tag, no Docker build/push"
            echo "  --push                 Push Docker image to registry after building"
            echo "  --registry HOST        Docker registry host (default: ghcr.io)"
            echo "  --repo ORG/REPO        GitHub repo used as image prefix"
            echo "                         (auto-detected from git remote if omitted)"
            echo "  --skip-branch-check    Allow release from a branch other than 'main'"
            echo "  -h, --help             Show this message"
            exit 0
            ;;
        *)
            _die "Unknown option: $1. Run with --help for usage."
            ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Derive metadata
# ---------------------------------------------------------------------------

cd "${SERVICE_DIR}"

# Version — sourced from pyproject.toml, the single source of truth.
VERSION=$(grep -E '^version\s*=' pyproject.toml | head -1 | sed 's/.*= *"//;s/".*//')
[[ -n "${VERSION}" ]] || _die "Could not parse version from pyproject.toml."

# Git context
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# Image repository prefix — inferred from git remote if not supplied.
if [[ -z "${REPO}" ]]; then
    REPO=$(git remote get-url origin 2>/dev/null \
        | sed -E 's|.*github\.com[:/]||; s|\.git$||' \
        | tr '[:upper:]' '[:lower:]') || true
fi

# Docker image tags follow the CD pipeline convention (cd.yml):
#   ghcr.io/<repo>/<service>:<version>
#   ghcr.io/<repo>/<service>:<sha>
#   ghcr.io/<repo>/<service>:latest
IMAGE_BASE="${REGISTRY}/${REPO}/${SERVICE_NAME}"
IMAGE_VERSION="${IMAGE_BASE}:${VERSION}"
IMAGE_SHA="${IMAGE_BASE}:${GIT_SHA}"
IMAGE_LATEST="${IMAGE_BASE}:latest"

# Git tag is scoped to the service to avoid collisions in the mono-repo.
GIT_TAG="tenant-management/v${VERSION}"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

echo ""
echo -e "${C_BOLD}Tenant Management — release.sh${C_RESET}"
echo -e "${C_DIM}  service  : ${SERVICE_NAME}"
echo -e "  version  : ${VERSION}"
echo -e "  branch   : ${GIT_BRANCH}  (${GIT_SHA})"
echo -e "  image    : ${IMAGE_VERSION}"
echo -e "  git tag  : ${GIT_TAG}"
[[ "${DRY_RUN}" == true ]] \
    && echo -e "  mode     : DRY-RUN — quality gate runs but no git/Docker side effects${C_RESET}" \
    || echo -e "${C_RESET}"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

_section "Pre-flight checks"

# 1. Clean working tree — never release uncommitted changes.
if ! git diff --quiet || ! git diff --cached --quiet; then
    _die "Uncommitted changes detected.\n       Commit or stash all changes before releasing."
fi
_ok "Working tree is clean"

# 2. Branch guard — default to main only; hotfix branches need --skip-branch-check.
if [[ "${SKIP_BRANCH_CHECK}" == false && "${GIT_BRANCH}" != "main" ]]; then
    _die "Refusing to release from branch '${GIT_BRANCH}'.\n       Switch to 'main' or pass --skip-branch-check."
fi
_ok "Branch: ${GIT_BRANCH}"

# 3. Version tag must not already exist.
if git tag --list | grep -qx "${GIT_TAG}"; then
    _die "Git tag '${GIT_TAG}' already exists.\n       Bump version in pyproject.toml before releasing."
fi
_ok "Git tag '${GIT_TAG}' is available"

# 4. Docker required for non-dry-run builds.
if [[ "${DRY_RUN}" == false ]] && ! command -v docker >/dev/null 2>&1; then
    _die "Docker is not installed or not in PATH."
fi
[[ "${DRY_RUN}" == false ]] && _ok "Docker is available"

# ---------------------------------------------------------------------------
# Quality gate  (mandatory — release cannot proceed on any failure)
# ---------------------------------------------------------------------------

_section "Quality gate"
echo ""

# lint.sh runs: ruff · ruff format · mypy · pylint · symilar CPD · pytest · bandit
# set -euo pipefail propagates — any failing check aborts the release here.
bash "${SCRIPTS_DIR}/lint.sh"

# ---------------------------------------------------------------------------
# Dry-run exit
# ---------------------------------------------------------------------------

if [[ "${DRY_RUN}" == true ]]; then
    _section "Dry-run complete — quality gate passed"
    echo ""
    _info "Would build  : ${IMAGE_VERSION}"
    _info "Would tag    : ${IMAGE_LATEST}"
    _info "Would tag    : ${IMAGE_SHA}"
    _info "Would create : git tag ${GIT_TAG}"
    [[ "${PUSH}" == true ]] && _info "Would push   : all image tags + git tag"
    echo ""
    _warn "No Docker build or git operations were performed."
    echo ""
    exit 0
fi

# ---------------------------------------------------------------------------
# Docker build
# ---------------------------------------------------------------------------

_section "Docker build"
echo ""

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

docker build \
    --label "org.opencontainers.image.title=tenant-management" \
    --label "org.opencontainers.image.version=${VERSION}" \
    --label "org.opencontainers.image.revision=${GIT_SHA}" \
    --label "org.opencontainers.image.created=${BUILD_DATE}" \
    --label "org.opencontainers.image.source=https://github.com/${REPO}" \
    -t "${IMAGE_VERSION}" \
    -t "${IMAGE_LATEST}" \
    -t "${IMAGE_SHA}" \
    .

echo ""
_ok "Built  : ${IMAGE_VERSION}"
_ok "Tagged : ${IMAGE_LATEST}"
_ok "Tagged : ${IMAGE_SHA}"

# ---------------------------------------------------------------------------
# Git tag
# ---------------------------------------------------------------------------

_section "Git tag"

git tag -a "${GIT_TAG}" -m "Release tenant-management v${VERSION}

Built from ${GIT_BRANCH}@${GIT_SHA} on ${BUILD_DATE}."

_ok "Created annotated tag: ${GIT_TAG}"

# ---------------------------------------------------------------------------
# Push (optional)
# ---------------------------------------------------------------------------

if [[ "${PUSH}" == true ]]; then
    _section "Push — Docker registry"
    echo ""

    docker push "${IMAGE_VERSION}"
    _ok "Pushed: ${IMAGE_VERSION}"

    docker push "${IMAGE_LATEST}"
    _ok "Pushed: ${IMAGE_LATEST}"

    docker push "${IMAGE_SHA}"
    _ok "Pushed: ${IMAGE_SHA}"

    _section "Push — git tag"

    git push origin "${GIT_TAG}"
    _ok "Pushed: ${GIT_TAG}"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

_section "Release complete"
echo ""
_ok "${C_BOLD}tenant-management v${VERSION}${C_RESET} is ready"
echo ""

if [[ "${PUSH}" == false ]]; then
    echo -e "${C_DIM}  Next steps — push when ready:"
    echo -e "    docker push ${IMAGE_VERSION}"
    echo -e "    docker push ${IMAGE_LATEST}"
    echo -e "    docker push ${IMAGE_SHA}"
    echo -e "    git push origin ${GIT_TAG}${C_RESET}"
fi
echo ""
