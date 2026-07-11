# Storefront Service

Tenant-scoped e-commerce backend (catalog + cart + orders) for the platform,
built on **physical-silo multi-tenancy**: each shop's data lives in its own
database, resolved per request from the `X-Tenant-ID` header
(`app/infrastructure/database/tenant_routing.py`).

- **Port:** 8025
- **Stack:** FastAPI (async), SQLAlchemy 2 async, Alembic, `uv`. PostgreSQL via
  `asyncpg`; tests use `sqlite+aiosqlite`.

## Domain

| Area | Endpoints |
|---|---|
| Categories | `POST/GET /api/v1/categories`, `DELETE /categories/{id}` |
| Products | `POST/GET /api/v1/products`, `GET/PATCH/DELETE /products/{id}` |
| Variants | `POST /products/{id}/variants`, `DELETE /products/{id}/variants/{vid}` |
| Cart | `POST /api/v1/carts`, `GET /carts/{id}`, item add/update/remove |
| Orders | `POST /api/v1/orders/checkout`, `GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/status` |

Clothing-first: products carry a base price; **variants** are the buyable
`(size, color)` combinations that hold their own SKU, optional price override,
and stock. Checkout converts a cart into an immutable order (line items snapshot
name/SKU/price), decrements variant stock, and marks the cart checked-out.

Money is stored as integer minor units (`*_cents`). Order lifecycle:
`pending → paid → fulfilled`, with `cancelled` reachable from `pending`/`paid`.

## Run

```bash
uv sync
# migrate a tenant's silo database (siloed mode is ON by default)
uv run python -m scripts.tenant_migrations provision <tenant_id>
uv run gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 5 -b 0.0.0.0:8025
```

Set `SILOED_MULTITENANCY_ENABLED=false` to run in shared-schema mode against a
single `DATABASE_URL` (handy for local dev / tests).

## Quality

```bash
bash scripts/lint.sh   # ruff + ruff format --check + mypy --strict + pytest
```
