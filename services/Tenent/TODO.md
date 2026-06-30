# Tenent Service — TODO

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
