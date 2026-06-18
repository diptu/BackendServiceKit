# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is the `iam` service — the active microservice within **BackendServiceKit**, a modular Python microservices monorepo. The IAM service is a stateful, dual-token (access + refresh JWT) Identity and Access Management engine built on FastAPI + SQLAlchemy async + PostgreSQL.

The monorepo root is two levels up (`../../`). Other planned services (notification, payment, etc.) exist only as scaffolding. All substantive work lives under `services/iam/`.

---

## Commands

All commands run from `services/iam/` unless noted. The package manager is `uv`.

### Run the service
```bash
uvicorn app.main:app --reload --port 8000
```

### Tests
```bash
# All tests
uv run pytest

# Single test file
uv run pytest tests/test_login.py -v

# Single test by name
uv run pytest tests/test_login.py::TestLogin::test_login_success -v

# With output (no capture)
uv run pytest -s
```

Tests use `sqlite+aiosqlite:///:memory:?cache=shared` — no real DB needed.

### Lint & format
```bash
uv run ruff check .           # lint
uv run ruff check --fix .     # auto-fix lint
uv run ruff format .          # format
uv run mypy --explicit-package-bases .  # type check
```

### Taskfile (from monorepo root)
```bash
task test:one SERVICE=iam     # run IAM tests
task lint                     # lint all services
task format                   # format all services
task typecheck                # mypy all services
task quality                  # format + lint + typecheck + test
task dev                      # docker compose up --build (all services)
```

---

## Architecture

### Request flow
```
HTTP request
  → FastAPI router (app/api/v1/auth.py)
  → Depends(get_auth_service) injects AuthService
  → AuthService calls UserRepository / RoleRepository
  → SQLAlchemy AsyncSession (from get_async_db → get_db)
  → PostgreSQL (asyncpg driver)
```

### Dependency injection chain
- `app/api/v1/dependencies.py` — `get_async_db()` wraps the lower-level `get_db()` from `app/db/session.py`
- `app/db/session.py` — lazily initializes a single `AsyncEngine` + `async_sessionmaker` from `settings.DATABASE_URL`
- Tests override `get_db` (not `get_async_db`) via `app.dependency_overrides`

### Auth flow
1. **Register** — hashes password (bcrypt), assigns `DEFAULT_ROLE` (`guest`), creates `User` + `UserRole` rows. Raises `409` on duplicate email.
2. **Login** — verifies password, builds JWT claims (`sub`, `email`, `jti`, `roles`, `permissions`, `type`), mints access token (15 min) + refresh token (7 days). Stores refresh JTI in `ACTIVE_REFRESH_TOKENS` (in-process dict — not persistent across restarts).

### RBAC
- Roles defined in `app/core/rbac.py` as `RoleEnum` (StrEnum): `super_admin`, `admin`, `manager`, `operator`, `auditor`, `support`, `service_account`, `guest`, `user`.
- Default on registration: `guest`. After verification: `user`. First bootstrap: `super_admin`.
- JWT claims embed role names and flattened permission names directly — downstream services can verify without a DB round-trip.

### Policy engine
`app/policy_engine/` is a stub engine (evaluator, context, decision, effect, registry) intended for ABAC-style policy evaluation. JSON policy examples live in `app/policies/examples/`. Not yet wired into any API endpoint.

### Key models
- `User` — core identity. `ACTIVE_REFRESH_TOKENS` is a module-level dict on this file (not a DB table).
- `Role` / `Permission` / `RolePermission` — RBAC join tables.
- `UserRole` — many-to-many between User and Role.
- `UserProfile` / `UserSocialLink` — extended user metadata (separate from auth).

### Configuration
`app/core/config.py` uses `pydantic-settings`. It loads `.env` from the project root (`services/iam/.env`). The only required env var at runtime is `DATABASE_URL`. `SECRET_KEY` has an insecure dev fallback — always override in any real environment.

### Testing patterns
- `conftest.py` creates a fresh in-memory SQLite DB per test function, overrides `get_db`, and provides `client` (HTTPX `AsyncClient` over ASGI transport).
- `TestLogin` uses `mocker.patch` on `AuthService.login` to avoid DB interaction.
- `TestRegister` hits the real endpoint with the real service but patches `hash_password`.
- Tests are async; the anyio backend is forced to `asyncio` via the `anyio_backend` fixture.
- Mark async tests with `@pytest.mark.anyio`.
