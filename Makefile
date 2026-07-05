\
# BackendServiceKit — build orchestration.
#
# Usage: make <target> [SERVICE=<name>] [VAR=value]
# Run `make` or `make help` to list targets.

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

COMPOSE_FILE := docker-compose.yml

# Auto-discovered from services/*/pyproject.toml — mirrors the same `find`
# .github/workflows/ci.yml uses, so this list can't drift out of sync as
# services are added or removed.
SERVICES := $(shell find services -maxdepth 2 -name pyproject.toml -exec dirname {} \; | xargs -n1 basename | sort)
TARGET_SERVICES := $(if $(SERVICE),$(SERVICE),$(SERVICES))
REV ?= -1

.PHONY: help
help: ## List available targets
	@echo "Discovered services: $(SERVICES)"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =========================
# SERVICE SCAFFOLDING
# =========================

.PHONY: new
new: ## Create a new service skeleton (NAME required, e.g. make new NAME=Payment)
	@test -n "$(NAME)" || (echo "NAME is required, e.g. make new NAME=Payment" && exit 1)
	mkdir -p services/$(NAME)/app/api services/$(NAME)/app/core
	mkdir -p services/$(NAME)/tests
	touch services/$(NAME)/app/main.py
	touch services/$(NAME)/pyproject.toml
	touch services/$(NAME)/uv.lock
	touch services/$(NAME)/.env.example
	@echo "Created service: $(NAME)"

# =========================
# TODOs
# =========================

.PHONY: todos-sync
todos-sync: ## Synchronize all service-level TODOs into the root TODO.md
	python scripts/todo_manager.py --sync

# =========================
# TESTING
# =========================

.PHONY: test
test: ## Run tests for SERVICE, or every discovered service if SERVICE is unset
	@set -e; for s in $(TARGET_SERVICES); do \
		echo "🧪 Running tests for services/$$s..."; \
		(cd services/$$s && uv run pytest) || [ $$? -eq 5 ] || exit 1; \
	done

# =========================
# LINT / FORMAT / TYPECHECK
# =========================

.PHONY: lint
lint: ## Lint SERVICE, or every discovered service if SERVICE is unset (ruff check)
	@set -e; for s in $(TARGET_SERVICES); do \
		echo "🔍 Linting $$s"; \
		(cd services/$$s && uv run ruff check .); \
	done

.PHONY: typecheck
typecheck: ## Strict mypy type-check for SERVICE, or every discovered service
	@set -e; for s in $(TARGET_SERVICES); do \
		echo "🧪 Type checking services/$$s..."; \
		(cd services/$$s && uv run mypy --explicit-package-bases .); \
	done

.PHONY: format
format: ## Format, sort imports, and auto-fix lint issues for SERVICE (or all)
	@set -e; for s in $(TARGET_SERVICES); do \
		echo "✨ Linting and formatting services/$$s..."; \
		(cd services/$$s && uv run ruff check --select I --fix . && uv run ruff check --fix . && uv run ruff format .); \
	done

.PHONY: quality
quality: format lint typecheck test ## Full local quality gate: format → lint → typecheck → test

# =========================
# DATABASE MIGRATIONS (ALEMBIC)
# =========================

.PHONY: migrate
migrate: ## Apply alembic migrations up to head (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make migrate SERVICE=IAM" && exit 1)
	@test -f services/$(SERVICE)/alembic.ini || (echo "services/$(SERVICE)/alembic.ini not found — alembic isn't configured for this service." && exit 1)
	cd services/$(SERVICE) && uv run alembic upgrade head

.PHONY: migrate-downgrade
migrate-downgrade: ## Roll back alembic migrations (SERVICE required, REV=-1 by default)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make migrate-downgrade SERVICE=IAM" && exit 1)
	@test -f services/$(SERVICE)/alembic.ini || (echo "services/$(SERVICE)/alembic.ini not found — alembic isn't configured for this service." && exit 1)
	cd services/$(SERVICE) && uv run alembic downgrade $(REV)

.PHONY: migrate-revision
migrate-revision: ## Create a new alembic revision (SERVICE and MESSAGE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make migrate-revision SERVICE=IAM MESSAGE='add x'" && exit 1)
	@test -n "$(MESSAGE)" || (echo "MESSAGE is required, e.g. make migrate-revision SERVICE=IAM MESSAGE='add x'" && exit 1)
	@test -f services/$(SERVICE)/alembic.ini || (echo "services/$(SERVICE)/alembic.ini not found — alembic isn't configured for this service." && exit 1)
	cd services/$(SERVICE) && uv run alembic revision --autogenerate -m "$(MESSAGE)"

.PHONY: migrate-current
migrate-current: ## Show the current alembic revision applied (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make migrate-current SERVICE=IAM" && exit 1)
	@test -f services/$(SERVICE)/alembic.ini || (echo "services/$(SERVICE)/alembic.ini not found — alembic isn't configured for this service." && exit 1)
	cd services/$(SERVICE) && uv run alembic current

.PHONY: migrate-history
migrate-history: ## Show full alembic migration history (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make migrate-history SERVICE=IAM" && exit 1)
	@test -f services/$(SERVICE)/alembic.ini || (echo "services/$(SERVICE)/alembic.ini not found — alembic isn't configured for this service." && exit 1)
	cd services/$(SERVICE) && uv run alembic history --verbose

# =========================
# DEV INFRASTRUCTURE (DOCKER COMPOSE — all services)
# =========================

.PHONY: dev
dev: ## Run all services (docker compose up --build)
	docker compose -f $(COMPOSE_FILE) up --build

.PHONY: dev-down
dev-down: ## Stop all services
	docker compose -f $(COMPOSE_FILE) down

.PHONY: dev-logs
dev-logs: ## Tail logs for all services
	docker compose -f $(COMPOSE_FILE) logs -f

.PHONY: logs
logs: ## Tail logs for a single service (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make logs SERVICE=iam" && exit 1)
	docker compose -f $(COMPOSE_FILE) logs -f $(SERVICE)

# =========================
# DOCKER — SINGLE SERVICE OPS
# =========================

.PHONY: docker-build
docker-build: ## Build a single service image (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make docker-build SERVICE=iam" && exit 1)
	docker compose -f $(COMPOSE_FILE) build $(SERVICE)

.PHONY: docker-up
docker-up: ## Build and run a single service (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make docker-up SERVICE=iam" && exit 1)
	docker compose -f $(COMPOSE_FILE) up --build $(SERVICE)

.PHONY: docker-down
docker-down: ## Stop a single service (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make docker-down SERVICE=iam" && exit 1)
	docker compose -f $(COMPOSE_FILE) stop $(SERVICE)

.PHONY: docker-logs
docker-logs: ## Tail logs for a single service (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make docker-logs SERVICE=iam" && exit 1)
	docker compose -f $(COMPOSE_FILE) logs -f $(SERVICE)

.PHONY: docker-rebuild
docker-rebuild: ## Clean rebuild of a single service, no cache (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make docker-rebuild SERVICE=iam" && exit 1)
	docker compose -f $(COMPOSE_FILE) build --no-cache $(SERVICE)

.PHONY: clean-docker
clean-docker: ## Tear down containers/volumes, prune docker, clear __pycache__/*.pyc
	docker compose -f $(COMPOSE_FILE) down -v
	docker system prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

# =========================
# LOCAL CI
# Mirrors .github/workflows/ci.yml stage-by-stage:
#   Stage 1 — uv sync --all-groups   (remote: Install dependencies)
#   Stage 2 — ruff check .           (remote: Run lint)
#   Stage 3 — pytest -q              (remote: Run tests)
# DATABASE_URL matches the remote runner env variable precisely.
# =========================

.PHONY: ci-local
ci-local: ## Run the full CI pipeline locally for every discovered service (or CI_SERVICES override)
	@command -v uv >/dev/null || (echo "'uv' is not installed. Run: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
	@set -e; \
	passed=0; \
	for s in $(if $(CI_SERVICES),$(CI_SERVICES),$(SERVICES)); do \
		if [ ! -f "services/$$s/pyproject.toml" ]; then \
			echo "⏭  Skipping services/$$s — no pyproject.toml (scaffolded but not active)"; \
			continue; \
		fi; \
		echo ""; \
		echo "══════════════════════════════════════════════════════"; \
		echo "  CI LOCAL  ▶  services/$$s"; \
		echo "══════════════════════════════════════════════════════"; \
		echo "  [1/3] Installing / syncing dependencies..."; \
		(cd services/$$s && uv sync --all-groups --quiet); \
		echo "  [2/3] Lint check (ruff check — read-only, matches remote)..."; \
		(cd services/$$s && uv run ruff check .); \
		echo "  [3/3] Test suite (pytest -q)..."; \
		(cd services/$$s && DATABASE_URL="sqlite+aiosqlite:///test_db.sqlite" uv run pytest -q); \
		echo "  ✓ services/$$s passed all CI checks"; \
		passed=$$((passed + 1)); \
	done; \
	echo ""; \
	echo "══════════════════════════════════════════════════════"; \
	printf "  CI LOCAL PASSED — %s service(s) clean\n" "$$passed"; \
	echo "══════════════════════════════════════════════════════"
	@find . -name "test_db.sqlite" -delete 2>/dev/null || true

.PHONY: ci-local-one
ci-local-one: ## Run the CI pipeline locally for a single service (SERVICE required)
	@command -v uv >/dev/null || (echo "'uv' is not installed. Run: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make ci-local-one SERVICE=IAM" && exit 1)
	@test -f services/$(SERVICE)/pyproject.toml || (echo "services/$(SERVICE)/pyproject.toml not found — is SERVICE='$(SERVICE)' correct?" && exit 1)
	@echo "══════════════════════════════════════════════════════"
	@echo "  CI LOCAL  ▶  services/$(SERVICE)"
	@echo "══════════════════════════════════════════════════════"
	@echo "  [1/3] Installing / syncing dependencies..."
	cd services/$(SERVICE) && uv sync --all-groups --quiet
	@echo "  [2/3] Lint check (ruff check — read-only, matches remote)..."
	cd services/$(SERVICE) && uv run ruff check .
	@echo "  [3/3] Test suite (pytest -q)..."
	cd services/$(SERVICE) && DATABASE_URL="sqlite+aiosqlite:///test_db.sqlite" uv run pytest -q
	@echo "  ✓ services/$(SERVICE) passed all CI checks"
	@find . -name "test_db.sqlite" -delete 2>/dev/null || true

# =========================
# CI/CD EMULATION (act)
# Runs GitHub Actions workflows inside Docker containers on the local machine.
# One-time setup: Docker Desktop running, `brew install act`, and
# `cp .secrets.local.example .secrets.local`. Configuration is read from
# .actrc (checked in) — no per-command flags needed.
# =========================

.PHONY: ci-emulate
ci-emulate: ## Emulate the full GitHub Actions CI pipeline locally via act
	@command -v docker >/dev/null || (echo "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker" && exit 1)
	@docker info >/dev/null 2>&1 || (echo "Docker daemon is not running. Start Docker Desktop and retry." && exit 1)
	@command -v act >/dev/null || (echo "act not installed. macOS: brew install act" && exit 1)
	@test -f .secrets.local || (echo ".secrets.local not found. Create it: cp .secrets.local.example .secrets.local" && exit 1)
	act push --workflows .github/workflows/ci.yml --secret-file .secrets.local --env-file .env.act

.PHONY: ci-emulate-one
ci-emulate-one: ## Emulate CI for one matrix service via act (SERVICE required)
	@test -n "$(SERVICE)" || (echo "SERVICE is required, e.g. make ci-emulate-one SERVICE=IAM" && exit 1)
	@command -v docker >/dev/null || (echo "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker" && exit 1)
	@docker info >/dev/null 2>&1 || (echo "Docker daemon is not running. Start Docker Desktop and retry." && exit 1)
	@command -v act >/dev/null || (echo "act not installed. macOS: brew install act" && exit 1)
	@test -f .secrets.local || (echo ".secrets.local not found. Create it: cp .secrets.local.example .secrets.local" && exit 1)
	@test -f services/$(SERVICE)/pyproject.toml || (echo "services/$(SERVICE)/pyproject.toml not found — is SERVICE='$(SERVICE)' correct?" && exit 1)
	act push --workflows .github/workflows/ci.yml --matrix service:$(SERVICE) --secret-file .secrets.local --env-file .env.act

.PHONY: cd-emulate
cd-emulate: ## Emulate the GitHub Actions CD pipeline via act (requires a real GHCR PAT)
	@command -v docker >/dev/null || (echo "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker" && exit 1)
	@docker info >/dev/null 2>&1 || (echo "Docker daemon is not running. Start Docker Desktop and retry." && exit 1)
	@command -v act >/dev/null || (echo "act not installed. macOS: brew install act" && exit 1)
	@test -f .secrets.local || (echo ".secrets.local not found. cp .secrets.local.example .secrets.local — needs a real GITHUB_TOKEN with packages:write scope." && exit 1)
	@test -f Dockerfile.service || (echo "Dockerfile.service not found at repository root — required by cd.yml." && exit 1)
	act push --workflows .github/workflows/cd.yml --secret-file .secrets.local --env-file .env.act --privileged $(ACT_FLAGS)
