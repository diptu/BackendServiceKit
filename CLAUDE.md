# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**BackendServiceKit** is a mono-repo reference architecture of production-grade Python microservices. It targets enterprise SaaS platforms: multi-tenant IAM, ABAC/RBAC, billing, notifications, observability, etc. Seven services under `services/*/` are fully active implementations with real code, migrations, and passing test suites; every other `services/*/` directory is still a design doc (README-only) showing planned architecture.

**Phase 2** (see `PHASE2.md`) will rewrite performance-critical services in Rust (tonic/axum/gRPC). Python is the current Phase 1 implementation language.

## Active Services

All seven live under `services/<Name>/` with the same layout (see "App Layer Structure" below) and the same stack. Every other `services/*/` directory contains only a `README.md`.

| Service | Port | What it owns |
|---|---|---|
| **IAM** | 8022 | Roles, permissions, groups, entitlements, access reviews, ABAC policy evaluation engine, `UserProjection` (read-only). |
| **Authentication** | 8024 | Credentials (the only place a password hash exists), JWT access tokens, rotating/revocable refresh tokens, sessions, audit log. MFA/OAuth2.1/OIDC/SSO not yet built — see `services/Authentication/TODO.md`. |
| **User** | 8023 | Identity CRUD, status lifecycle, profile/preferences/avatar/contacts, platform invitations. Merges what were UserManagement + UserLifecycleManagement + UserProfileManagement. |
| **Tenent** | 8005 | Tenant CRUD, lifecycle state machine, cross-tenant isolation policy/resource claims. Merges TenantManagement + TenantLifecycle + TenantIsolation. |
| **OrganizationManagement** | 8021 | Org hierarchy, teams, memberships, invitations. |
| **APIGateway** | 8080 (Kong: 8000) | Reverse proxy + Redis cache + Celery workers. Verifies every proxied request's JWT locally and overrides the client-supplied `X-Tenant-ID` with the verified claim before forwarding (see `app/services/token_verifier.py`) — everything except `/api/v1/auth/**` requires a valid `Authorization: Bearer` token. |
| **ObservilityManagement** | 8020 | Merges what would have been seven separate services (Logging, Tracing, Metrics, Monitoring, Alerting, Observability, Health Check) into one container. |

### Stack

- Python 3.11.9 (pinned in `.python-version`), FastAPI (async ASGI), SQLAlchemy 2 async, Alembic
- Package manager: `uv` (not pip/poetry)
- Database: PostgreSQL via `asyncpg`; tests use `sqlite+aiosqlite`
- Linter/formatter: `ruff`; type checker: `mypy --strict`

### Config

Every active service has its own `services/<Name>/app/core/config.py` — pydantic-settings `Settings` class, `@lru_cache` singleton, all env vars map 1-to-1. IAM's is shown below as the reference example:

| Var | Default |
|-----|---------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_identity` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` |
| `SECRET_KEY` | `CHANGE_ME` |
| `ENVIRONMENT` | `development` |

Docs (`/docs`, `/redoc`, `/openapi.json`) are disabled when `ENVIRONMENT=production`.

`SECRET_KEY`/`JWT_ALGORITHM`/`JWT_ISSUER` must be identical across **Authentication** and **APIGateway** specifically — Authentication signs (HS256, shared secret), APIGateway verifies locally rather than calling back over HTTP (same reasoning Tenent's `IsolationService.resolve_context` already used). A real deployment should move this to asymmetric RS256 signing — see `services/Authentication/TODO.md`.

### App Layer Structure

```
services/<Name>/app/
├── main.py                     # FastAPI app factory
├── core/config.py              # Settings (pydantic-settings)
├── api/v1/                     # Route handlers
├── models/                     # SQLAlchemy ORM models
├── schemas/                    # Pydantic request/response schemas
├── domain/                     # Enums, events, exceptions
├── infrastructure/
│   ├── database/engine.py      # AsyncEngine creation
│   ├── database/session.py     # async_sessionmaker (SessionLocal)
│   └── database/dependencies.py # FastAPI get_db() dependency
├── repositories/               # Tenant-scoped data access (tenant_id is a required kwarg, not optional)
└── services/                   # Business logic
```

`repositories/` and `services/` are fully implemented in every active service — none of them are stubs. (ObservilityManagement is the one structural outlier: it uses a `domains/<bounded-context>/` vertical-slice layout instead of this horizontal one — not yet reconciled or documented as an intentional exception.)

### Key Design Decisions

- **UserProjection model**: IAM holds a local read-only materialized view of user data from the User Service, updated via async domain events (`user.created`, `user.updated`, `user.deleted`). It intentionally never stores passwords, MFA secrets, or PII — Authentication owns the only password hash in the platform. This eliminates synchronous cross-service dependencies during authorization.
- **Tenant-scoped queries**: All IAM (and every other service's) queries are tenant-scoped, with `tenant_id` a required keyword argument on repository lookups — never optional. The `user_projections` table has a composite index on `(tenant_id, email)`.
- **No foreign keys to external services**: The projection pattern is enforced — models do not reference other services' tables via FK; cross-service references are plain columns.
- **Gateway-enforced trust boundary**: APIGateway verifies the caller's JWT and is the only source of truth for `X-Tenant-ID` forwarded to every other service — a service should never trust that header from anywhere except the gateway.

### IAM Data Hierarchy

```
Tenant → Organization → Workspace → Team → Members
                     └→ Group
                     └→ Resources
```

Authorization flow: `User → Roles → Permissions → ABAC Policy Engine → Resource` — the ABAC engine is implemented (`services/IAM/app/services/policy_evaluation_service.py`, `POST /api/v1/authorization/evaluate`): it evaluates a tenant's active policies against subject (+ optional resource) attributes, falls back to plain RBAC permission grants when no policy matches, and default-denies otherwise.

## Commands

All commands use `make` (Makefile) from the repo root, or `uv run` from inside a service directory. Run `make help` to list every target — `SERVICES` is auto-discovered from `services/*/pyproject.toml`, so it never needs manual updates as services are added.

### Testing

```bash
# Run IAM tests (from repo root)
make test SERVICE=IAM

# Run from inside service directory
cd services/IAM && uv run pytest

# Run a single test file
cd services/IAM && uv run pytest tests/unit/test_health.py

# Run with output
cd services/IAM && uv run pytest -v
```

Test `DATABASE_URL` must be `sqlite+aiosqlite:///test_db.sqlite` (the `ci-local` target sets this automatically).

### Linting & Formatting

```bash
# Format + fix imports + lint one service
make format SERVICE=IAM

# Auto-fix formatting (runs ruff check --fix + ruff format)
cd services/IAM && bash scripts/fix.sh

# Full lint check: ruff lint + format check + mypy + pytest (used by CI)
cd services/IAM && bash scripts/lint.sh

# Type check only
cd services/IAM && uv run mypy .
```

### Full Quality Gate (mirrors CI)

```bash
# All checks for IAM: format → lint → typecheck → test
make quality SERVICE=IAM

# Mirrors GitHub Actions ci.yml exactly (sets DATABASE_URL), every discovered service
make ci-local

# Same, but scoped to one service
make ci-local-one SERVICE=IAM
```

### Database Migrations (Alembic)

All migration commands require `SERVICE=IAM` from the repo root:

```bash
make migrate SERVICE=IAM                                # Apply to head
make migrate-revision SERVICE=IAM MESSAGE="add x"       # Create autogenerated revision
make migrate-downgrade SERVICE=IAM REV=-1               # Roll back one step
make migrate-current SERVICE=IAM                        # Show applied revision
make migrate-history SERVICE=IAM                        # Show full history
```

### Dev Infrastructure

```bash
make dev                       # docker compose up --build (all services)
make dev-down                  # docker compose down
make docker-up SERVICE=IAM     # Single service
```

### Scaffolding

```bash
make new NAME=Payment                          # Scaffold a new service skeleton at the mono-repo level
cd services/IAM && bash scripts/bootstrap.sh  # First-time setup for IAM (venv, deps, .env, migrations)
```

## CI/CD

- CI (`ci.yml`): finds all `pyproject.toml` under `services/*/` (search depth 3 — `services/<Name>/pyproject.toml`; don't shrink this back to depth 2, that bug previously made CI discover zero services and report green on every push), runs `uv sync --frozen` → `scripts/lint.sh` (ruff + mypy + pytest) → `docker build`. The `lint.sh` script is what CI actually executes — keep it as the authoritative quality gate. Every active service must have its own `scripts/fix.sh`/`scripts/lint.sh` and both `mypy`/`ruff` declared in its own `pyproject.toml` dev dependencies — without the latter, `uv run mypy`/`uv run ruff` silently fall back to whatever's on the system `PATH` instead of the service's own locked versions (this happened to Tenent and APIGateway; fixed, but worth checking for any new service).
- CD (`cd.yml`): builds and pushes Docker images to GHCR for every service in its `strategy.matrix.service` list — this list is NOT auto-discovered, add new services to it by hand.
- Local emulation via `act`: `make ci-emulate` / `make cd-emulate` (requires Docker + `act` + `.secrets.local`).

## Shared Directory

`shared/` contains cross-service libraries: `observability/` is fully implemented (OTel tracing/metrics/logging SDK) and consumed by all seven active services. `cache/`, `messaging/`, `middleware/`, `utils/` remain empty `__init__.py` placeholders — not yet implemented. (Every service currently rolls its own Redis/RabbitMQ/rate-limit wiring directly rather than through a shared layer — worth consolidating there eventually, e.g. the gateway's JWT-verification middleware would be a natural fit for `shared/middleware/` once a second service needs the identical check.)

## Implementation Order

Active (Phase 1): IAM, Authentication, User, Tenent, OrganizationManagement, APIGateway, ObservilityManagement. Per `Implementation-order.md`'s original phased plan, Authentication and ABAC were meant to come later — both got pulled forward and built directly against IAM's existing RBAC data model rather than waiting for their own dedicated phases. Still not built: Session Management (beyond Authentication's own refresh-token sessions), MFA, SSO/OIDC, Resources, Audit Logging (beyond each service's own local audit tables), and the remaining rows of `Implementation-order.md`.

# Tenant Lifecycle States

| State | Description | Key Rules |
|-------|-------------|-----------|
| **draft** | Tenant record created; no resources allocated. | Entry state. TM only. |
| **provisioning** | Async infra setup in progress (DB, API keys, VPC). | TL entry via `PUT /provisioning`. |
| **pending** | Provisioning done; awaiting compliance/confirmation. | Must pass through before active. |
| **active** | Fully operational and billed. | Normal operating state. |
| **suspended** | Service paused — non-payment or policy violation. | Data retained. Reversible via reactivate. |
| **locked** | Security hold; admin-triggered for investigation. | TL-only (TM proxies as suspended). Reversible via unlock. |
| **archived** | Cold storage after contract end; no production access. | Prerequisite for deletion. |
| **deleted** | Soft-delete. Hard purge by Offboarding Service post-retention. | Terminal state. |

## State Machine Flow

```
TM:  draft → provisioning → pending → active ⇄ suspended
                                            ↘ archived → deleted
TL:           provisioning → pending → active ⇄ suspended
                                            ↓         ↘ archived → deleted
                                          locked → active
```

## Service Responsibilities

TenantManagement (TM) and TenantLifecycle (TL) below describe roles, not separate services — both were merged into **Tenent** (`services/Tenent/`, port 8005; see `services/Tenent/TODO.md`). The distinction is now in-process, not a network boundary: `TenantService` (TM role) does authoritative CRUD and owns `draft`/`provisioning`/`pending`/`active`/`suspended`/`archived`/`deleted`; `TenantLifecycleService` (TL role) drives all transitions and calls `TenantService` directly (no HTTP) to keep it in sync. TL still owns the additional `locked` state (proxied to TM's model as `suspended`).

## Key Transition Rules

- `provisioning → pending` requires explicit `POST /pend` (not auto-advanced)
- `pending → active` requires explicit `PUT /activate` (compliance gate)
- `locked` is TL-only; lock/unlock syncs TM as suspend/activate
- `deleted` is terminal — no further transitions allowed