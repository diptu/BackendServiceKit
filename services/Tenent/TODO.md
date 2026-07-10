# Tenent Service — TODO

## Siloed Multi-tenancy Standard — Control Plane

**Status: Control Plane implemented (opt-in); physical DB orchestration still
blocked.** In the platform's north-star Siloed (database-per-tenant) model
(root `README.md` → "Core Architectural Pillars (Target)"), **Tenent owns the
Control Plane** — the authoritative registry that maps every tenant/subdomain
to its database. This is the piece every other service's connection router and
the gateway's subdomain resolver depend on. This pass builds that registry.

### Key design decision: the Control Plane is global, not siloed

A registry of *all* tenants' databases cannot itself be per-tenant. The
`tenant_connections` table lives in Tenent's own single database — this is the
one place in the platform that is intentionally **not** database-per-tenant.
Tenant-scoped operational tables could silo later; the registry never does.

### Implemented in this pass

- **`TenantConnection` model** (`app/models/tenant_connection.py`) — one global
  registry row per tenant: subdomain + connection coordinates
  (driver/host/port/name/user) + a `secret_ref`. **No raw password is ever
  stored** — only a reference resolved at connect time.
- **`ControlPlaneService`** (`app/services/control_plane_service.py`):
  `register` / `resolve_subdomain` (gateway entry point, no credentials) /
  `get_connection` / `build_dsn` (assembles the full URL via a
  `SecretsProvider`, fails closed on a missing secret) / `deprovision`.
- **`SecretsProvider`** (`app/infrastructure/secrets.py`) — `EnvSecretsProvider`
  stand-in so credentials stay out of the registry; swap for Vault/KMS in prod.
- **API** (`app/api/v1/control_plane_router.py`, all internal-only):
  `POST /control-plane/connections/{id}`, `GET /control-plane/resolve?subdomain=`,
  `GET /control-plane/connections/{id}`, `GET …/{id}/dsn`,
  `DELETE …/{id}`.
- **Lifecycle wiring** (opt-in `control_plane_auto_register`, default off):
  entering `provisioning` registers the tenant's DB home; `delete` disables it.
  Best-effort/fire-and-log, never fatal to the transition — so existing
  behaviour is unchanged when off.
- **Consumer bridge**: `shared/db/ControlPlaneConnectionResolver` — the
  production replacement for IAM's `TemplateConnectionResolver`, reading each
  tenant's DSN back out of Tenent. IAM/User/Org swap to it with no other change.
- **Verified**: 41/41 tests (12 new in `tests/unit/test_control_plane.py`,
  incl. subdomain uniqueness, credential assembly + URL-encoding, fail-closed
  on missing secret, deprovision, and the shared resolver reading a DSN
  end-to-end from Tenent's app); ruff clean; 0 new mypy errors.

### Still blocked / not Tenent-only

- [ ] Physical database provisioning (`CREATE DATABASE` + run each service's
      migrations into the new tenant DB) triggered from the `provisioning`
      state — needs the per-service migration orchestrators (IAM's exists).
- [ ] Physical drop/archive on offboarding (registry disable is done).
- [ ] Real secrets backend (Vault/KMS) behind `SecretsProvider`.
- [ ] Gateway Tenant Resolver middleware calling `GET /control-plane/resolve`
      — APIGateway's piece.
- [ ] Service-to-service auth so `/control-plane/**` (registration + `/dsn`)
      is locked to trusted internal callers, not the public gateway.

### How to turn on auto-registration

```bash
CONTROL_PLANE_AUTO_REGISTER=true
TENANT_DB_HOST=pgbouncer
TENANT_DB_NAME_TEMPLATE=tenant_{tenant}       # {tenant}=hex id, {name}=slug
TENANT_SUBDOMAIN_TEMPLATE={name}
TENANT_DB_SECRET_REF_TEMPLATE=tenant/{name}/db  # resolved via SecretsProvider
```

## In Progress

- [ ] Wire RabbitMQ event publishing on tenant state transitions (`tenant.status_changed`)
- [ ] Persist access decision logs to DB (currently in-memory stub)

## Planned

### API
- [ ] `GET /api/v1/tenants/{id}/audit-log` — paginated tenant audit trail
- [ ] `POST /api/v1/isolation/bulk-validate` — batch cross-tenant validation (up to 100 pairs)
- [ ] Cursor pagination on `GET /api/v1/isolation/decisions` (already on tenants list)

### State Machine
- [ ] Grace period enforcement before `suspended → archived` transition
- [ ] `archived → deleted` auto-schedule after retention period (configurable TTL)
- [ ] Webhook delivery on lifecycle transitions (outbound HTTP to tenant-configured URL)

### Isolation
- [ ] Attribute-based policy evaluation (ABAC) beyond strict/partner types
- [ ] Cache stampede protection (probabilistic early expiry for hot policies)
- [ ] Audit log persistence — write `AccessDecisionLog` rows to DB for compliance reporting

### Observability
- [ ] SQLAlchemy instrumentation (`instrument_sqlalchemy(engine)`) after engine creation in lifespan
- [ ] Custom `isolation_cache_hits_total` / `isolation_cache_misses_total` counters exported via OTel MeterProvider
- [ ] Structured audit trail log line per isolation decision (JSON, includes trace_id)

### Testing
- [ ] Integration tests with real PostgreSQL (currently SQLite in tests)
- [ ] Integration tests with real Redis for isolation cache hit/miss paths
- [ ] Contract tests for event schema (`tenant.status_changed` payload)
- [ ] Load test: isolation check throughput target — 5,000 rps at p99 < 10ms

### Technical Debt
- [ ] `base.py` repository class — add `count()` method to avoid `SELECT *` for pagination totals
- [ ] Consolidate `TenantContactRepository` — contacts are internal (no public API); consider removing the table
- [ ] Replace `python-jose` with `PyJWT` (python-jose is unmaintained since 2023)
- [ ] Alembic migration for `access_decision_logs` composite index `(caller_tenant_id, decided_at DESC)`

## Completed

- [x] **Control Plane registry** for Siloed multi-tenancy — see the top section
- [x] Merged TenantManagement + TenantLifecycle + TenantIsolation into single service
- [x] Global exception handlers (no try/except in route handlers)
- [x] Redis warm-up with fault-tolerant startup
- [x] OTel tracing + metrics wired in lifespan
- [x] Gunicorn + `opentelemetry-instrument` Dockerfile CMD
- [x] ReadinessChecker on `/ready` (real Postgres + Redis probes)
- [x] JSON structured logging via `configure_logging()`
- [x] Rate limiting via SlowAPI
- [x] Request ID middleware
- [x] Schema barrel exports (`app/schemas/__init__.py`)
- [x] Repository barrel exports (`app/repositories/__init__.py`)
- [x] `openapi_tags` wired from `app/core/openapi.py`
- [x] `scripts/lint.sh` and `scripts/fix.sh`
