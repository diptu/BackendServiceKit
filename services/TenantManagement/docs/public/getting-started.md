# Getting Started

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11.9 |
| PostgreSQL | 15+ |
| `uv` | latest (`pip install uv`) |
| Docker | optional — for full-stack compose |

---

## Local Development

```bash
# 1. Enter the service directory
cd services/TenantManagement

# 2. First-time setup (idempotent)
bash scripts/bootstrap.sh
```

`bootstrap.sh` will:

1. Copy `.env.example` → `.env` (if `.env` does not already exist)
2. Install dependencies via `uv sync`
3. Apply all database migrations (`alembic upgrade head`)

Then start the dev server:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Interactive docs are available at <http://localhost:8000/docs>.

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` · `staging` · `production` |
| `DEBUG` | `false` | Enables debug-level logging |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_tenant` | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `20` | SQLAlchemy connection pool size |
| `DATABASE_MAX_OVERFLOW` | `40` | Max connections above pool size |
| `DATABASE_POOL_TIMEOUT` | `30` | Seconds to wait for a connection |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis (rate limiting, caching) |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ (domain event publishing) |
| `RABBITMQ_EXCHANGE` | `tenant.events` | Exchange name for outbound events |
| `SECRET_KEY` | `CHANGE_ME` | **Change in every environment** |
| `RATE_LIMIT_ENABLED` | `true` | Enable per-client rate limiting |
| `DEFAULT_RATE_LIMIT` | `100/minute` | Default rate limit |
| `CORS_ALLOW_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `ENABLE_METRICS` | `true` | Expose Prometheus metrics at `/metrics` |

> **Production note:** API docs (`/docs`, `/redoc`, `/openapi.json`) are automatically disabled when `ENVIRONMENT=production`.

---

## Docker

The service ships a two-stage Dockerfile. The final image runs as a non-root user (`appuser`, UID 10001).

```bash
# Build
docker build -t tenant-management .

# Run (requires a .env file)
docker run -p 8000:8000 --env-file .env tenant-management
```

The entrypoint applies pending Alembic migrations before starting Gunicorn (4 workers, `UvicornWorker`).

---

## Full Stack (docker-compose)

```bash
# From the mono-repo root — starts all services
task dev

# Stop
task dev:down
```

---

## Running Tests

```bash
# From inside the service directory
uv run pytest -v

# Full quality gate (format + lint + type check + tests)
bash scripts/lint.sh
```

Tests use an in-memory SQLite database — no PostgreSQL required.

---

## Seeding Data

```bash
uv run python scripts/seed.py
```

Creates sample tenants across all lifecycle states for local development.
