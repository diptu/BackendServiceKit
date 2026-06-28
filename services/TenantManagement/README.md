# Tenant Management Service

## Overview

The **Tenant Management Service** is the authoritative system of record for all tenant data in the NutraTenant SaaS platform. It owns the complete lifecycle, configuration, ownership, and metadata for every customer (tenant).

A **tenant** is the top-level isolation boundary — every organization, workspace, resource, and user is ultimately scoped to a single tenant.

| Property | Value |
|---|---|
| Port | `8000` |
| API prefix | `/api/v1` |
| Database | PostgreSQL (asyncpg) — `nutratenant_tenant` |
| Runtime | Python 3.11.9 · FastAPI · SQLAlchemy 2 async |
| Package manager | `uv` |

---

## Architecture

This service follows the Enterprise Clean Architecture standard. All code lives under `app/`:

```
app/
├── api/v1/
│   ├── tenants_router.py     # All tenant CRUD, lifecycle, and sub-resource endpoints
│   └── health_router.py      # /health and /ready probes
├── domain/
│   ├── commands.py           # CreateTenantCmd, UpdateTenantCmd, AddOwnerCmd, …
│   ├── enums.py              # TenantStatus, OwnerRole, VALID_TRANSITIONS
│   ├── events.py             # TenantCreated, TenantActivated, TenantSuspended, …
│   └── exceptions.py         # TenantNotFoundError, TenantLockedError, …
├── services/
│   ├── tenant_service.py         # CRUD + lifecycle orchestration
│   ├── tenant_settings_service.py
│   ├── tenant_owner_service.py
│   └── tenant_metadata_service.py
├── infrastructure/
│   ├── database/
│   │   ├── base.py           # SQLAlchemy DeclarativeBase
│   │   ├── engine.py         # AsyncEngine factory
│   │   ├── session.py        # async_sessionmaker
│   │   ├── dependencies.py   # FastAPI get_db() dependency
│   │   ├── utils.py          # SSL URL normalisation
│   │   └── models/           # ORM models (Tenant, TenantContact, …)
│   └── repositories/         # TenantRepository, TenantSettingsRepository, …
└── schemas/
    └── tenant.py             # Pydantic request/response schemas (API layer only)
```

**Layer dependency rule:** `api → services → domain ← infrastructure`. The `api` layer translates Pydantic schemas into domain commands before calling services. Services accept only domain command objects — no Pydantic imports cross into the service layer.

### Tenant State Machine

```
draft ──► provisioning ──► active ◄──► suspended
                              │               │
                              └───────────────┴──► archived ──► deleted
```

| State | Description |
|---|---|
| `draft` | Record created; no resources allocated. Entry state. |
| `provisioning` | Async infra setup in progress (DB, API keys, VPC). |
| `active` | Fully operational and billed. |
| `suspended` | Service paused — non-payment or policy violation. Data retained. |
| `archived` | Read-only cold storage after contract end. Prerequisite for deletion. |
| `deleted` | Soft-delete. Hard purge by Offboarding Service post-retention. |

### Domain Events

Every state-changing operation publishes a domain event (logged via `logger.debug`; replace with a message broker in production):

| Event | Trigger |
|---|---|
| `TenantCreated` | `POST /tenants` |
| `TenantUpdated` | `PATCH /tenants/{id}` |
| `TenantProvisioningStarted` | `POST /{id}/provision` |
| `TenantActivated` | `POST /{id}/activate` (from provisioning) |
| `TenantReactivated` | `POST /{id}/activate` (from suspended) |
| `TenantSuspended` | `POST /{id}/suspend` |
| `TenantArchived` | `POST /{id}/archive` |
| `TenantDeleted` | `DELETE /{id}` |
| `TenantConfigurationUpdated` | `PATCH /{id}/settings` |
| `TenantOwnerAdded` | `POST /{id}/owners` |
| `TenantOwnerRemoved` | `DELETE /{id}/owners/{owner_id}` |

### Database Tables

| Table | Description |
|---|---|
| `tenants` | Master tenant record (name, status, region, locale, owner_id) |
| `tenant_settings` | One row per tenant — timezone, locale, theme, session timeout |
| `tenant_contacts` | Owners and admins; soft-removable; enforces ≥1 active owner |
| `tenant_metadata` | Arbitrary key-value pairs per tenant (schema-free) |

---

## Setup

### Prerequisites

- Python 3.11.9
- PostgreSQL 15+
- `uv` package manager (`pip install uv`)
- Docker (optional, for full stack)

### Local Development

```bash
# 1. Clone and enter the service directory
cd services/TenantManagement

# 2. Install dependencies
uv sync

# 3. Copy environment config
cp .env.example .env
# Edit DATABASE_URL, SECRET_KEY, REDIS_URL as needed

# 4. Apply database migrations
alembic upgrade head

# 5. Start the service
uv run uvicorn app.main:app --reload --port 8000
```

### Docker

The service uses a two-stage Docker build: a `builder` stage installs dependencies with `uv`, and a locked-down `runtime` stage runs the application as a non-root user (`appuser`, UID 10001).

```bash
# Build
docker build -t tenant-management .

# Run
docker run -p 8000:8000 --env-file .env tenant-management
```

The container entrypoint runs `alembic upgrade head` before starting Gunicorn:

```
[entrypoint] Running Alembic migrations...
[entrypoint] Migrations complete. Starting application...
```

**Runtime:** Gunicorn with `UvicornWorker`, 4 workers, bound to `0.0.0.0:8000`.

### Full Stack (docker-compose)

```bash
# From repo root
task dev
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `false` | Enable debug logging |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_tenant` | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `20` | SQLAlchemy connection pool size |
| `DATABASE_MAX_OVERFLOW` | `40` | Max connections above pool size |
| `DATABASE_POOL_TIMEOUT` | `30` | Seconds to wait for a connection |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis connection (rate limiting, caching) |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection |
| `RABBITMQ_EXCHANGE` | `tenant.events` | Exchange for domain event publishing |
| `SECRET_KEY` | `CHANGE_ME` | **Must be changed in production** |
| `RATE_LIMIT_ENABLED` | `true` | Enable request rate limiting |
| `DEFAULT_RATE_LIMIT` | `100/minute` | Default rate limit per client |
| `CORS_ALLOW_ORIGINS` | `["http://localhost:3000", ...]` | Allowed CORS origins |
| `ENABLE_METRICS` | `true` | Expose Prometheus metrics |
| `ENABLE_TRACING` | `true` | Enable OTLP distributed tracing |
| `OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry collector endpoint |

---

## API Reference

All endpoints are prefixed `/api/v1`. Interactive docs available at `/docs` and `/redoc` in non-production environments.

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` if the process is alive |
| `GET` | `/ready` | Readiness probe — confirms database and dependencies are reachable |

---

### Tenants — Core CRUD

#### `POST /api/v1/tenants` — Create tenant

Creates a new tenant in `draft` state. Atomically writes three rows: the `Tenant` record, a seeded `TenantSettings` row, and an initial owner `TenantContact`.

**Request body**

```json
{
  "name": "alphabet-corp",
  "display_name": "Alphabet Corporation",
  "description": "Optional free-text description.",
  "owner_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "region": "us-east-1",
  "timezone": "America/New_York",
  "locale": "en-US",
  "currency": "USD"
}
```

> `name` (slug) must match `^[a-z0-9][a-z0-9-]*[a-z0-9]$` and is **immutable** after creation.

**Responses:** `201 Created` · `409 Conflict` (name taken) · `422 Unprocessable Entity`

---

#### `GET /api/v1/tenants` — List tenants

Returns a cursor-paginated list. Soft-deleted tenants are excluded by default.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by lifecycle state |
| `region` | string | Filter by deployment region |
| `search` | string | Substring match against name or display name |
| `limit` | integer (1–100) | Page size (default `20`) |
| `next_cursor` | string | Opaque cursor from previous response |

**Response**

```json
{
  "items": [{ "id": "...", "name": "alphabet-corp", "status": "active", ... }],
  "total": 42,
  "next_cursor": "eyJpZCI6IjU1MG...",
  "has_more": true
}
```

---

#### `GET /api/v1/tenants/{tenant_id}` — Get tenant

Returns the full tenant record. **Responses:** `200 OK` · `404 Not Found`

---

#### `PATCH /api/v1/tenants/{tenant_id}` — Update tenant

Partial update of mutable fields. All fields are optional.

```json
{
  "display_name": "Alphabet Corp (Updated)",
  "timezone": "Europe/London",
  "locale": "en-GB",
  "currency": "GBP"
}
```

> `name`, `id`, `created_at` are immutable.

**Responses:** `200 OK` · `404 Not Found` · `423 Locked` (archived tenant)

---

#### `DELETE /api/v1/tenants/{tenant_id}` — Soft-delete tenant

Tenant must be in `archived` state. Sets `deleted_at`; the name slug remains reserved.

**Responses:** `204 No Content` · `409 Conflict` (not archived) · `404 Not Found`

---

### Tenants — Lifecycle Transitions

All transition endpoints accept an optional body `{ "reason": "..." }`.

| Method | Path | Transition | Valid From |
|---|---|---|---|
| `POST` | `/api/v1/tenants/{id}/provision` | `draft → provisioning` | `draft` |
| `POST` | `/api/v1/tenants/{id}/activate` | `→ active` | `provisioning`, `suspended` |
| `POST` | `/api/v1/tenants/{id}/suspend` | `active → suspended` | `active` |
| `POST` | `/api/v1/tenants/{id}/archive` | `→ archived` | `active`, `suspended` |

**Responses:** `200 OK` (with updated tenant body) · `409 Conflict` (invalid source state) · `404 Not Found`

---

### Tenant Settings

Per-tenant configuration. One settings record per tenant.

#### `GET /api/v1/tenants/{tenant_id}/settings`

Returns the full settings record including timezone, locale, language, date/number format, currency, session timeout, and theme.

#### `PATCH /api/v1/tenants/{tenant_id}/settings`

Partial update — only provided fields are changed.

```json
{
  "timezone": "America/Chicago",
  "session_timeout_minutes": 30,
  "default_theme": "dark"
}
```

**Responses:** `200 OK` · `404 Not Found` · `423 Locked` (archived tenant)

---

### Tenant Owners

Manages the list of `owner` and `admin` contacts for a tenant. **Invariant:** at least one active owner must remain at all times.

#### `GET /api/v1/tenants/{tenant_id}/owners`

Returns all active (non-removed) owners and admins.

#### `POST /api/v1/tenants/{tenant_id}/owners`

Adds a user as an owner or admin.

```json
{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "role": "owner"
}
```

**Responses:** `201 Created` · `409 Conflict` (user already active)

#### `DELETE /api/v1/tenants/{tenant_id}/owners/{owner_id}`

Soft-removes a contact. Returns `422` if it would remove the last active owner.

---

### Tenant Metadata

Schema-free key-value pairs per tenant. No migration needed to add new metadata fields.

#### `GET /api/v1/tenants/{tenant_id}/metadata`

Returns all key-value entries, ordered by key.

#### `PATCH /api/v1/tenants/{tenant_id}/metadata`

Upserts key-value pairs. Existing keys are overwritten; unmentioned keys are untouched. Set value to `""` to logically clear a key.

```json
{
  "metadata": {
    "industry": "FinTech",
    "customer_tier": "gold",
    "company_size": "enterprise"
  }
}
```

**Responses:** `200 OK` · `423 Locked` (archived tenant)

---

## Testing

```bash
# Run all tests (from repo root)
task test SERVICE=tenantmanagement

# Or from inside the service directory
cd services/TenantManagement && uv run pytest

# With output
uv run pytest -v
```

Tests use SQLite in-memory (`sqlite+aiosqlite:///:memory:`) — no PostgreSQL required.

## Quality Gate

```bash
# Full check: format → lint → typecheck → test
task quality SERVICE=tenantmanagement

# Or from inside the service
bash scripts/lint.sh
```
