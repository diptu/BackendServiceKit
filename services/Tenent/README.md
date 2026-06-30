# Tenent — Combined Tenant Service

A unified FastAPI service merging **TenantManagement**, **TenantLifecycle**, and **TenantIsolation** into a single deployable unit. Runs at port **8005** behind Kong.

## Purpose

Provides the complete tenant boundary layer for the NutraTenant SaaS platform:

- **Tenant Management** — authoritative CRUD for tenant records (draft → active lifecycle, settings, owners, metadata)
- **Tenant Lifecycle** — strict state machine with full event history (provisioning, pending, activate, suspend, lock, archive, delete)
- **Tenant Isolation** — cross-tenant access enforcement with Redis-cached policy evaluation

## Stack

- Python 3.11.9 · FastAPI · SQLAlchemy 2 async · Alembic · asyncpg
- Redis (isolation policy cache + rate-limit store)
- OpenTelemetry SDK (traces + metrics via OTel Collector)
- Gunicorn + UvicornWorker + `opentelemetry-instrument` prefix

## API Endpoints

| Tag | Mount | Description |
|-----|-------|-------------|
| Tenants | `/api/v1/tenants` | Core CRUD, settings, owners, metadata |
| Tenant Lifecycle | `/api/v1/tenants/{id}/lifecycle` | TM-facing state transitions |
| Lifecycle | `/api/v1/lifecycle` | TL state machine + event history |
| Isolation | `/api/v1/isolation` | Policy CRUD, access checks, resource claims |
| Health | `/health`, `/ready` | Liveness + readiness probes |

Interactive docs: `GET /docs` (disabled in `production` environment).

## Tenant Lifecycle State Machine

```
draft → provisioning → pending → active ⇄ suspended
                                       ↘ archived → deleted
                              locked → active   (TL only)
```

All state transitions enforce the state machine — invalid transitions return `409 Conflict`.

## Key Design Decisions

- **In-process sync**: TM↔TL state sync happens via in-process service calls (no HTTP round-trips).
- **Redis-first isolation**: Policy lookups are Redis-cached (TTL 120s strict / 300s claim) to avoid DB on every request.
- **Global exception handlers**: All domain exceptions are mapped in `main.py`; route handlers never catch domain errors.
- **OTel zero-code**: `opentelemetry-instrument` wraps gunicorn — no telemetry code in business logic.

## Dependencies

| Service | Role |
|---------|------|
| PostgreSQL | Primary store (tenants, lifecycle, isolation policies, claims) |
| Redis | Isolation policy cache + rate-limiting |
| OTel Collector | Receives OTLP gRPC traces + metrics |

## Configuration

Key env vars (see `app/core/config.py` for full list):

| Var | Default |
|-----|---------|
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `ENVIRONMENT` | `development` |
| `OTEL_SERVICE_NAME` | `tenent` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` |

## Development

```bash
# Install deps
cd services/Tenent && uv sync

# Run tests
uv run pytest

# Auto-fix formatting
bash scripts/fix.sh

# Full quality gate (ruff + mypy + pytest)
bash scripts/lint.sh

# Run locally
uv run uvicorn app.main:app --reload --port 8005
```

## Events

Domain events are published to RabbitMQ on tenant state changes:
- `tenant.created`, `tenant.updated`, `tenant.deleted`
- `tenant.status_changed` (carries `from_status` + `to_status`)
- `tenant.lifecycle.transitioned`
