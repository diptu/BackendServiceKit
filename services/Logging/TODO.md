# Logging Service — TODO

**Status: Phases 1–9 and 11 implemented.** See "Implementation Notes" at the
bottom for two things that changed shape during the build versus what this
plan originally assumed.

## Design Decisions (read first — these shape every phase below)

Constraints this plan is built around, discovered by inspecting the current
stack before writing a single line:

1. **Ingestion already exists — do not build a second one.**
   `Tenent` and `APIGateway` both call `configure_logging()`
   (`shared/observability/logging/logger.py`) which writes one JSON line per
   log record to stdout. `promtail` (`services/Logging/promtail/promtail-config.yaml`)
   already scrapes every container's stdout via the Docker socket and pushes
   to `loki` (`services/Logging/loki/loki-config.yaml`) under the `observability`
   compose profile. **This means zero code changes are required in Tenent or
   APIGateway to get their logs into Loki — that pipeline is live today.**
   The Logging service must not introduce a competing ingestion path for
   traffic that already flows through promtail.

2. **Loki is the system of record. The Logging service does not duplicate storage.**
   No Postgres models, no migrations, no local log table. The service is a
   domain/API layer in front of Loki's HTTP API (`/loki/api/v1/query_range`,
   `/loki/api/v1/query`, `/loki/api/v1/push`, `/loki/api/v1/label`). This
   avoids "spamming" the codebase with a second storage engine that would
   drift out of sync with the one that already works.

3. **`auth_enabled: false` in loki-config.yaml means Loki itself has zero
   tenant isolation.** Today nothing stops one caller from reading another
   tenant's logs if they can reach port 3100 directly. The Logging service
   is the enforcement boundary — it must never be bypassed. Loki's port
   3100 must stay internal-network-only (already true — no host mapping
   change needed), and the app must reject requests to `/logs/*` that don't
   already carry a validated `tenant_id`.

4. **`GET /logs/{id}` and `DELETE /logs/{id}` from the README are aspirational
   — Loki has no concept of a stable per-line ID and no per-line delete.**
   Retention is bulk, time-window based (`table_manager.retention_period` in
   loki-config.yaml, currently 168h). This plan implements `{id}` as a
   synthetic, computable-not-stored key (stream labels + nanosecond
   timestamp + line hash) and implements `DELETE` as a coarse, admin-only,
   filter-based erasure request — not a per-row delete. This is called out
   explicitly so nobody is surprised later that "delete one log line" isn't
   real in a Loki-backed system.

5. **Every touch to Tenent/APIGateway is additive, one line, and copies an
   existing pattern already used for other upstreams** (e.g. how
   `TenantProvisioning` was registered in APIGateway's `RouteService`). No
   refactors, no new middleware classes, no changes to how those services log.

---

## Phase 1 — Scaffold (no business logic)

- [x] Create `services/Logging/app/` mirroring the Enterprise Clean
      Architecture layout used by Tenent/APIGateway: `api/v1/`, `core/`,
      `domain/`, `infrastructure/`, `repositories/`, `schemas/`, `services/`
      (no `models/` — no DB tables owned by this service)
- [x] `pyproject.toml` + `uv.lock` (Python 3.11.9, FastAPI, httpx, pydantic-settings) — copy Tenent's as a base, strip SQLAlchemy/Alembic/asyncpg deps
- [x] `app/core/config.py` — `Settings` (pydantic-settings, `@lru_cache`): `LOKI_BASE_URL` (default `http://loki:3100`), `SERVICE_NAME=logging`, `JWT_AUTH_ENABLED`, `SECRET_KEY`, `ENVIRONMENT`
- [x] `app/core/logging.py` — thin wrapper calling `shared.observability.logging.logger.configure_logging(service_name="logging")` (dogfood the existing SDK; do not write a second formatter)
- [x] `app/main.py` — FastAPI app factory, lifespan startup: build shared `httpx.AsyncClient` for Loki, wire OTel per `shared/observability/instrumentation/fastapi.py`
- [x] `app/api/v1/health_router.py` — `/health` (liveness) + `/ready` (readiness probe: `GET {LOKI_BASE_URL}/ready`)
- [x] `Dockerfile` — copy Tenent's pattern (gunicorn + `opentelemetry-instrument` CMD)
- [x] `.env.example`
- [x] `scripts/lint.sh`, `scripts/fix.sh` (copy from Tenent, no service-specific changes needed)

## Phase 2 — Loki client (read path only)

- [x] `app/infrastructure/loki/loki_client.py` — async httpx wrapper: `query_range()`, `query()`, `labels()`, `label_values()`. No business logic — raw LogQL in, parsed streams out.
- [x] `app/domain/exceptions.py` — `LokiUnavailableError`, `LokiQueryError`, `InvalidLogQLError`
- [x] `app/domain/log_entry.py` — internal dataclass: `timestamp`, `level`, `service`, `trace_id`, `span_id`, `message`, `tenant_id`, `raw_labels`, `raw_line`
- [x] `app/repositories/log_repository.py` — translates filter args (tenant_id, service, user_id, level, time range, free-text) into a LogQL selector string; parses Loki's stream response into `LogEntry` objects. This is the *only* place LogQL syntax is constructed.

## Phase 3 — Tenant scoping / RBAC (before any endpoint is exposed publicly)

- [x] `app/middleware/auth.py` — copy Tenent's `verify_token()` JWT-bearer pattern verbatim (same `python-jose`, same `settings.secret_key`/`jwt_algorithm` fields) — do not invent a new auth mechanism
- [x] `app/api/v1/dependencies.py` — `require_tenant_scope()` dependency: extracts `tenant_id` from the validated JWT claims (or `X-Tenant-ID` header when called gateway-to-service, matching how `ProxyService` already forwards tenant context); injects a mandatory `tenant_id=` LogQL label matcher into every query built downstream. No endpoint may build a Loki query without this dependency in its signature.
- [x] Platform-admin escape hatch: a `roles` claim of `platform-admin` skips the forced tenant filter (needed for the `/logs/service/{service}` cross-tenant ops view) — gate behind an explicit role check, not just "no tenant_id".

## Phase 4 — Read API (the core value — ship this before ingestion/export)

- [x] `GET /api/v1/logs/search` — query params: `tenant_id` (forced/validated, see Phase 3), `service`, `level`, `q` (free-text line filter), `from`, `to`, `limit`, `cursor` — proxies to `log_repository` → `loki_client.query_range()`
- [x] `GET /api/v1/logs/tenant/{tenant_id}` — thin wrapper over `/search` with `tenant_id` fixed; 403 if caller's own tenant_id doesn't match and caller lacks `platform-admin`
- [x] `GET /api/v1/logs/service/{service}` — thin wrapper over `/search` with `service` fixed; platform-admin only (spans tenants)
- [x] `GET /api/v1/logs/user/{user_id}` — wrapper filtering on the `user_id` extra field (present only for services that log it via `extra={"user_id": ...}` — already supported today by `OTelJSONFormatter`'s passthrough of `extra`, zero changes needed upstream)
- [x] `app/schemas/log.py` — `LogEntryResponse`, `LogSearchResponse` (paginated, cursor-based to match the convention already used on `GET /api/v1/tenants`)

## Phase 5 — Ingestion escape hatch (additive, not a replacement for promtail)

- [x] `POST /api/v1/logs` — single structured log event, **only for emitters that cannot log to stdout under promtail's reach** (e.g. browser/mobile clients, third-party webhook receivers, serverless functions). Validates against `LogEntryCreate` schema, stamps `received_at` + enriches OTel `trace_id`/`span_id` from the current span (via `shared/observability/logging/correlation.py get_trace_context()`), forwards to `loki_client.push()`
- [x] `POST /api/v1/logs/bulk` — same, batch of up to N (configurable, default 500) entries in one push
- [x] Document explicitly in the OpenAPI description: internal services should keep logging to stdout as today — this endpoint is not the ingestion path for Tenent/APIGateway

## Phase 6 — `{id}`-addressed endpoints (document + implement the constraint from Decision #4)

- [x] Define synthetic id encoding — implemented as `base64url(json({"s": service, "l": level, "ts": timestamp_ns, "h": line_hash}))` (reversible, not a one-way hash, so it can rebuild a targeted query — see `app/domain/log_id.py`)
- [x] `GET /api/v1/logs/{id}` — decode id → targeted LogQL query scoped to the encoded labels + a tight `from`/`to` window around the timestamp → verify line hash matches → 404 if not found (covers both "wrong id" and "already outside retention window")
- [x] `DELETE /api/v1/logs/{id}` — chose the `501 Not Implemented` option (not the erasure-requests endpoint) for v1: platform-admin-gated, returns a body explaining the constraint and pointing at this TODO. The erasure-request endpoint (`POST /api/v1/logs/erasure-requests` against Loki's compactor delete API) is still a real option if a GDPR-style use case shows up — not built.

## Phase 7 — Export

- [x] `POST /api/v1/logs/export` — same filters as `/search`, streams NDJSON (or CSV) response using `StreamingResponse` + `loki_client.query_range()` pagination — synchronous streaming for MVP, no new worker infra
- [x] Backlog only (do not build in v1): async export via Celery if export volume grows past what a streaming HTTP response can hold — APIGateway already has a Celery+RabbitMQ worker pattern (`app/tasks/worker.py`) to copy if/when this becomes necessary

## Phase 8 — Observability for the Logging service itself

- [x] Dogfood `shared/observability`: `configure_logging()`, OTel tracing (`shared/observability/tracing/tracer.py`), `/metrics` via `shared/observability/exporters/prometheus.py` — same as Tenent, no new patterns
- [x] Custom counters: `logging_query_total{tenant_id,status}`, `logging_query_duration_seconds`, `logging_ingest_total` — via `shared/observability/metrics/registry.py`

## Phase 9 — Gateway integration (additive only — APIGateway changes)

- [x] `services/APIGateway/app/domain/enums.py` — add one `UpstreamService.LOGGING` member (mirrors existing `TENENT`, `TENANT_PROVISIONING`)
- [x] `services/APIGateway/app/core/config.py` — add one `logging_base_url: str` setting (mirrors `tenent_base_url`)
- [x] `services/APIGateway/app/services/route_service.py` — add one `Route(prefix="/api/v1/logs", upstream=UpstreamService.LOGGING, base_url=settings.logging_base_url, cache_ttl=0)` entry to `_build_registry()` — logs are not cacheable, `cache_ttl=0` or exclude from `CACHEABLE_METHODS`
- [x] `docker-compose.yml` — add `LOGGING_BASE_URL: http://logging:8000` to the `api-gateway` service's `environment:` block (one line, same as `TENENT_BASE_URL`)
- [x] No changes to `proxy_router.py`, `proxy_service.py`, or cache invalidation logic — the existing catch-all proxy already handles any registered route

## Phase 10 — Infra wiring

- [x] `docker-compose.yml` — new `logging` service block: `build: ./services/Logging`, `ports: ["8006:8000"]` (next free host port after 8001-8005), `environment: LOKI_BASE_URL=http://loki:3100`, same `backend` network, **no `profiles:` restriction and deliberately no `depends_on: loki`** (loki sits behind the `observability` profile — a hard `depends_on` on a profile-gated service would break `docker compose up` without `--profile observability`; the service degrades via `/ready` returning 503 instead)
- [x] Confirm `loki` port 3100 stays without a host mapping change / stays reachable only inside `backend` network from the Logging service — do not widen its exposure

## Phase 11 — Testing

- [x] Unit tests for `log_repository.py` LogQL construction (given filters → expected query string) — no real Loki needed
- [x] Unit tests for tenant-scope enforcement dependency (reject missing/mismatched tenant_id, allow platform-admin bypass)
- [ ] Integration tests against a real `loki` test container (`testcontainers`) for `/search`, `/logs` (POST), `/export` — mirrors the "replace fakeredis with testcontainers" tech debt item already tracked in `services/APIGateway/TODO.md`
- [x] Contract test: assert `OTelJSONFormatter`'s output (from `shared/observability/logging/json_formatter.py`) is parseable by the exact LogQL `| json` pipeline already configured in `promtail-config.yaml` — this is the one place a change to `shared/observability` could silently break the whole pipeline, so pin it with a test
- [ ] `task test SERVICE=Logging` wired into root `Taskfile.yml` service list once `pyproject.toml` exists

## Explicitly Out of Scope for v1

- Changing anything about how Tenent or APIGateway log (their stdout JSON pipeline already works)
- A second datastore for logs (Postgres/Elasticsearch) — Loki stays the only store
- Per-line delete as a real guarantee (see Decision #4 / Phase 6)
- Async export workers (Phase 7 backlog note)
- mTLS / advanced gateway hardening — inherits whatever APIGateway/Kong decide for all upstreams (see `services/APIGateway/TODO.md`)

## Implementation Notes (found while building, not obvious from the plan)

1. **`shared/observability` had to become best-effort, not a hard dependency.**
   Building and running the actual Docker image surfaced something the plan
   didn't account for: `shared/` lives at the repo root and is **not** copied
   into any service's Docker build context (each service's `context:` in
   `docker-compose.yml` is scoped to its own directory). Tenent/APIGateway
   already handle this correctly for `shared.observability.tracing` — it's
   wrapped in try/except in their lifespans. This service's `app/core/logging.py`
   and `app/services/log_ingest_service.py` originally imported
   `shared.observability.logging.*` unguarded, which crashed the container at
   import time. Both now try the shared import first and fall back to a local
   formatter/no-op — same resilience pattern as tracing, just applied to
   logging too. This is a repo-wide gap (worth fixing once, e.g. by installing
   `shared` as a proper path dependency in each service's `pyproject.toml`),
   not something specific to this service — out of scope to fix here.

2. **Tenent's own Dockerfile pattern (which this service's Dockerfile was
   based on) has two latent bugs**, both fixed locally in
   `services/Logging/Dockerfile` only (not touched in Tenent, per the
   "don't spam existing code" constraint):
   - `COPY pyproject.toml ./` before `RUN uv sync --frozen` never copies
     `uv.lock`, so `--frozen` always fails. Fixed here by also copying
     `uv.lock` in that step.
   - The runtime stage's `CMD` calls `uv run gunicorn ...`, but `uv` is a
     builder-stage-only tool (installed via `pip install uv`, never copied to
     the runtime image) — and the runtime `COPY --from=builder /root/.local
     /root/.local` copies a path uv never writes to (uv's venv lives at
     `/app/.venv`). Fixed here by dropping both: put `/app/.venv/bin` on
     `PATH` and invoke `gunicorn` directly, no `uv run` wrapper needed at
     runtime. Verified by actually building and running the image against a
     real Loki container (ingest → tenant-scoped search → cross-tenant 403 →
     `GET /{id}` → export, all exercised manually).
