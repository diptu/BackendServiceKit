# Distributed Tracing Service — TODO

**Status: Phases 1–10 implemented; Phase 11 partial.** See "Implementation
Notes" at the bottom for two things found by actually building and running
this against a real Tempo container — including a real bug in `tempo.yml`
itself that meant Tempo couldn't start at all.

Same shape as `services/Logging/` (see its `TODO.md` — implemented, and the
concrete pattern to copy structurally): a thin FastAPI query/API layer in
front of a specialized backend that already receives data today, not a
second ingestion path and not a second datastore. Where the two services'
constraints genuinely differ (see Decisions #3 and #5), this plan diverges
from Logging's on purpose — don't copy those two parts blindly.

## Design Decisions (read first — these shape every phase below)

Discovered by inspecting the current stack (docker-compose.yml, tempo.yml,
services/MetricsCollection/otelcol/config.yaml, shared/observability/tracing/*,
Tenent's and APIGateway's app/main.py) before writing a single line:

1. **Ingestion already exists — do not build a second one.**
   Tenent and APIGateway are both instrumented via OTel: `app/main.py`
   calls `configure_tracer()` + `instrument_fastapi()` / `instrument_httpx()`
   (Tenent also `instrument_redis()`) from `shared/observability/tracing/*`
   in their `lifespan()`, and both Dockerfiles wrap the process CMD in
   `opentelemetry-instrument` (auto-instrumentation). `otel-collector`
   (`services/MetricsCollection/otelcol/config.yaml`) already has a working
   `traces` pipeline — `receivers: [otlp]` → `processors: [memory_limiter,
   batch, transform/strip_sensitive, resource]` → `exporters: [otlp/tempo]`
   pointed at `tempo:4317`. Spans already flow into Tempo today under the
   `observability` compose profile. **This service queries Tempo — it does
   not receive OTLP itself.**

   Found but out of scope (a Tenent/APIGateway file, not touched here): the
   manual `configure_tracer(settings.app_name, settings.otlp_endpoint, ...)`
   call reads `settings.otlp_endpoint`, which pydantic-settings binds to env
   var `OTLP_ENDPOINT` — but `docker-compose.yml` only sets
   `OTEL_EXPORTER_OTLP_ENDPOINT` (the OTel-spec-standard var) for both
   `tenent` and `api-gateway`. Inside the container `settings.otlp_endpoint`
   silently falls back to its `http://localhost:4317` default, so the
   *manual* `configure_tracer()` / `instrument_fastapi()` / `instrument_httpx()`
   calls in those services' `app/main.py` are almost certainly dead weight —
   `trace.set_tracer_provider()` only takes effect on the first call, and the
   `opentelemetry-instrument` CLI wrapper (which *does* honor
   `OTEL_EXPORTER_OTLP_ENDPOINT` natively and auto-instruments FastAPI/httpx/
   redis before the app's own lifespan code even runs) very likely wins that
   race. Traces probably reach Tempo today via that auto-instrumentation
   path, not the `shared.observability` one. Don't be surprised the manual
   tracer setup appears to do nothing — and don't "fix" it as part of this
   service; it's out of scope.

2. **Tempo is the system of record. This service does not duplicate storage.**
   No Postgres, no Elasticsearch, no local span table. The service is a
   domain/API layer over Tempo's HTTP query API: `GET /api/traces/{traceID}`,
   `GET /api/search?q=<TraceQL>`, `GET /api/search/tags`,
   `GET /api/search/tag/{name}/values`, `GET /ready`.

   Found but relevant to Phase 5: Tempo's own `metrics_generator`
   (`tempo.yml`: `processors: [service-graphs, span-metrics]`) is configured
   to `remote_write` RED metrics to `http://prometheus:9090/api/v1/write` —
   but Prometheus's compose service has no `--web.enable-remote-write-receiver`
   flag (no `command:` override at all), so that push is silently rejected
   today. **Don't build `/traces/errors` or `/traces/slow` assuming
   Tempo-generated Prometheus metrics are populated — they aren't.** Use raw
   TraceQL search against Tempo directly for both.

3. **No tenant-isolation data exists on spans today** — unlike Logging,
   where `tenant_id` was at least present in every JSON log body.
   - `shared/observability/tracing/span_attributes.py` defines
     `set_tenant_span_attributes()` (stamps `tenant.id`, `request.id`, etc.
     on the active span) but grep confirms it is never called anywhere in
     Tenent or APIGateway.
   - FastAPI/httpx auto-instrumentation isn't configured to capture request
     headers either (`instrument_fastapi()` calls
     `FastAPIInstrumentor.instrument_app()` with no
     `http_capture_headers_server_request` — off by default), so
     `X-Tenant-ID` / `X-Request-ID` aren't recoverable from spans that way.
   - Consequence: a trace legitimately spans multiple services and shared
     infra (Kong, Redis, Postgres) with no reliable per-tenant identity
     anywhere in it today. Bolting on a Logging-style "tenant self-service"
     tier on top of that would either show nothing (filtering on an
     attribute that doesn't exist) or risk leaking cross-tenant data if the
     filter is ever loosened. **This service defaults to operator /
     platform-admin-only access for v1** — not the tenant-self-service model
     Logging uses. A `tenant_id` TraceQL filter is still built (Phase 4) as
     a forward-compatible no-op: it starts working the moment someone wires
     `set_tenant_span_attributes()` into Tenent/APIGateway — out of scope to
     do here.

4. **`DELETE /traces/{trace_id}` is aspirational**, same shape as Logging's
   equivalent decision. Tempo has no per-trace delete API — retention is
   bulk and time-based (`compactor.compaction.block_retention: 72h` in
   `tempo.yml`). Implement as `501 Not Implemented` with an explanation,
   admin-gated. Do not silently 404 forever and call it "deleted".

5. **No ingestion escape hatch — this is a real difference from Logging.**
   Logging's `POST /logs` / `POST /logs/bulk` existed because Loki's push
   API isn't something a browser or webhook can reasonably speak, and there
   was a genuine gap for non-containerized emitters. For traces,
   `otel-collector`'s OTLP HTTP receiver (port 4318) is already the
   standard, correct way for *any* OTel-capable emitter to submit a span
   directly. Building a bespoke ingestion endpoint here would just be a
   worse reimplementation of the OTLP wire protocol. Skip it entirely.

6. **Every touch to Tenent/APIGateway is additive, one line, and copies the
   pattern already used for Logging/TenantProvisioning** in APIGateway's
   `RouteService` — same `Route(...)` entry, same enum member, same one
   config field. No refactors, no new middleware.

7. **`tempo` sits behind the `observability` compose profile** (same as
   `loki`). No hard `depends_on: tempo` for the new service — same
   graceful-degradation-via-`/ready` pattern Logging uses for Loki (`/ready`
   returns 503 if Tempo isn't reachable instead of blocking the stack on an
   optional profile).

---

## Phase 1 — Scaffold (no business logic)

- [x] Create `services/DistributedTracing/app/` mirroring `services/Logging/app/`'s
      Enterprise Clean Architecture layout: `api/v1/`, `core/`, `domain/`,
      `infrastructure/`, `repositories/`, `schemas/`, `services/`, `middleware/`
      (no `models/` — no DB tables owned by this service)
- [x] `pyproject.toml` + `uv.lock` — copy `services/Logging/pyproject.toml` verbatim
      as a base (same deps: fastapi, httpx, pydantic-settings, python-jose, OTel
      exporter/instrumentation packages, prometheus-client)
- [x] `app/core/config.py` — `Settings`: `TEMPO_BASE_URL` (default
      `http://localhost:3200`), `TEMPO_TIMEOUT`, `SECRET_KEY`,
      `JWT_AUTH_ENABLED`, `JWT_ALGORITHM`, `ENVIRONMENT`, `CORS_ALLOW_ORIGINS`
- [x] `app/core/logging.py` — copy `services/Logging/app/core/logging.py`
      verbatim (best-effort `shared.observability` import with a local
      fallback formatter — see that file's docstring for why it can't be a
      hard dependency; same constraint applies here)
- [x] `app/main.py` — FastAPI app factory, lifespan startup: build a shared
      `httpx.AsyncClient` for Tempo, wire OTel per
      `shared/observability/instrumentation/fastapi.py` wrapped in
      try/except (same resilience pattern as Logging's `app/main.py`)
- [x] `app/api/v1/health_router.py` — `/health` (liveness) + `/ready`
      (readiness probe: `GET {TEMPO_BASE_URL}/ready`)
- [x] `Dockerfile` — copy `services/Logging/Dockerfile` **exactly**, including
      its two fixes over the Tenent-derived original: `COPY pyproject.toml
      uv.lock ./` (not just `pyproject.toml`) before `uv sync --frozen`, and
      no `uv run` wrapper in the runtime CMD (`uv` isn't installed there —
      call `gunicorn`/`opentelemetry-instrument` directly off `/app/.venv/bin`)
- [x] `.env.example`, `.dockerignore`
- [x] `scripts/lint.sh`, `scripts/fix.sh` (copy from Logging, no changes needed)

## Phase 2 — Tempo client (read path only)

- [x] `app/infrastructure/tempo/tempo_client.py` — async httpx wrapper:
      `trace_by_id(trace_id)` → `GET /api/traces/{traceID}`,
      `search(traceql, start, end, limit, spss)` → `GET /api/search`,
      `tag_names()` / `tag_values(name)` → `GET /api/search/tags` /
      `GET /api/search/tag/{name}/values`, `ready()` → `GET /ready`. No
      business logic — raw TraceQL in, parsed JSON out (mirrors
      `services/Logging/app/infrastructure/loki/loki_client.py` structure).
- [x] `app/domain/exceptions.py` — `TempoUnavailableError`, `TempoQueryError`,
      `InvalidTraceQLError`, `TraceNotFoundError`
- [x] `app/domain/span.py` — internal dataclasses: `Span` (span_id,
      parent_span_id, name, service, start_ns, duration_ns, status,
      attributes) and `Trace` (trace_id, root_span, spans: list[Span],
      duration_ns, service_names: set[str])
- [x] `app/repositories/trace_repository.py` — translates filter args
      (service, min_duration_ms, status, tenant_id, free-text attribute
      match) into a TraceQL query string; parses Tempo's `/api/traces/{id}`
      response (OTLP-shaped JSON: `batches[].scopeSpans[].spans[]`) into
      `Trace`/`Span` objects, and parses `/api/search` results into a
      lightweight trace-summary list. This is the *only* place TraceQL
      syntax is constructed (same rule Logging applies to LogQL).

## Phase 3 — Access control (operator-only — see Decision #3)

- [x] `app/middleware/auth.py` — copy `services/Logging/app/middleware/auth.py`
      verbatim (same JWT-bearer / `python-jose` pattern, no-op when
      `jwt_auth_enabled=False`)
- [x] `app/api/v1/dependencies.py` — `require_operator_scope()` dependency:
      requires a `roles` claim containing `platform-admin` (or
      `trace-viewer` if a narrower role is wanted) when
      `jwt_auth_enabled=True`; every `/traces/*` endpoint depends on this.
      Unlike Logging's `require_tenant_scope`, there is no per-tenant
      variant for v1 (see Decision #3) — this gates the whole service, not
      individual queries.
- [x] Optional `tenant_id` query param on `/traces/search` and friends,
      passed through to `trace_repository` as a TraceQL `{ .tenant_id =
      "..." }` (or `resource.tenant_id`, once someone decides which span it
      should land on) filter. Documented in the OpenAPI description as
      "currently a no-op until span tagging is added upstream" — do not
      remove this once it starts working; it's intentionally forward-compatible.

## Phase 4 — Read API

- [x] `GET /api/v1/traces/{trace_id}` — full trace fetch via
      `tempo_client.trace_by_id()`, parsed into a clean response (root span,
      flat span list, total duration, participating services). 404 via
      `TraceNotFoundError` if Tempo returns no data (covers both "bad id"
      and "outside the 72h retention window" — same ambiguity Logging's
      `GET /logs/{id}` documents for Loki).
- [x] `GET /api/v1/traces/{trace_id}/timeline` — same fetched trace,
      reshaped into a chronological (start-time-ordered) span list with
      relative offsets from the root span — a projection, not a second
      Tempo call.
- [x] `GET /api/v1/traces/{trace_id}/spans` — same fetched trace, flat span
      list with parent/child span_id references — another projection of the
      same fetch, no new Tempo call.
- [x] `GET /api/v1/traces/search` — query params: `service`, `min_duration_ms`,
      `status` (`ok` | `error`), `tenant_id` (see Phase 3), `q` (attribute
      key=value match), `start`, `end`, `limit` — built into TraceQL server
      side, proxies to `tempo_client.search()`
- [x] `app/schemas/trace.py` — `SpanResponse`, `TraceResponse`,
      `TraceSearchResponse` (list of trace summaries, not full traces — same
      convention Tempo's own `/api/search` uses, to keep search responses cheap)

## Phase 5 — Derived views (see Decision #2 — raw TraceQL, not Tempo-generated metrics)

- [x] `GET /api/v1/traces/service/{service}` — thin wrapper over `/search`
      with `resource.service.name` fixed; still gated by
      `require_operator_scope` (there is no cross/same-tenant distinction
      here per Decision #3 — everything is operator-only)
- [x] `GET /api/v1/traces/errors` — thin wrapper over `/search` with a
      `{ status = error }` TraceQL filter
- [x] `GET /api/v1/traces/slow` — thin wrapper over `/search` with a
      `{ duration > <min_duration_ms>ms }` TraceQL filter (query param,
      sensible default e.g. 500ms)

## Phase 6 — `DELETE /traces/{trace_id}` (implement the constraint from Decision #4)

- [x] `DELETE /api/v1/traces/{trace_id}` — **do not implement per-trace
      delete.** Return `501 Not Implemented`, admin-gated, with a body
      explaining that Tempo's retention is bulk/time-based
      (`block_retention: 72h`) and pointing back at this TODO. Mirrors
      Logging's `DELETE /logs/{id}` handler almost verbatim.

## Phase 7 — Export

- [x] `POST /api/v1/traces/export` — same filters as `/search`, streams
      NDJSON of trace summaries (or full traces, if requested via a
      `full=true` flag — note this means one Tempo `trace_by_id` call per
      result, so cap it harder than the summary case) using
      `StreamingResponse` — synchronous streaming for MVP, no new worker
      infra (same as Logging's Phase 7)

## Phase 8 — Observability for the service itself

- [x] Dogfood `shared/observability`: `configure_logging()`, OTel tracing,
      `/metrics` via `prometheus_client` — same as Logging, no new patterns.
      (Mildly funny but worth doing correctly: this is the *tracing* service
      instrumenting *itself* with tracing — make sure its own spans use a
      distinct `service.name` like `nutratenant-distributed-tracing` so they
      don't get confused with the data it's querying.)
- [x] Custom counters: `tracing_query_total{status}`,
      `tracing_query_duration_seconds`, `tracing_trace_fetch_total`

## Phase 9 — Gateway integration (additive only — APIGateway changes)

- [x] `services/APIGateway/app/domain/enums.py` — add one
      `UpstreamService.DISTRIBUTED_TRACING` member (mirrors `LOGGING`,
      `TENENT`, `TENANT_PROVISIONING`)
- [x] `services/APIGateway/app/core/config.py` — add one
      `distributed_tracing_base_url: str` setting
- [x] `services/APIGateway/app/services/route_service.py` — add one
      `Route(prefix="/api/v1/traces", upstream=UpstreamService.DISTRIBUTED_TRACING,
      base_url=settings.distributed_tracing_base_url, cacheable_methods=frozenset(),
      cache_ttl=0)` entry — traces are not cacheable, same reasoning as the
      `/api/v1/logs` route
- [x] `services/APIGateway/app/services/kong_admin_service.py` —
      `KONG_ROUTE_PREFIX_MAP` gets one more entry: `"/api/v1/traces":
      "nutratenant-distributed-tracing"`
- [x] Update the APIGateway tests that assert an exact route count (
      `test_route_service.py`, `test_gateway_router.py`,
      `test_kong_admin_service.py`, `test_proxy_router.py`) — this bit us
      once already when Logging was added: the count/prefix-set/cacheable-
      methods assertions all need the new route added, not just the number
      bumped. Check every hardcoded route-count assertion, not just the
      obvious ones — Logging's rollout found one hiding in
      `test_gateway_status_probes_unique_upstreams_only` (unique-upstream
      count, not route count) too.
- [x] `docker-compose.yml` — add `DISTRIBUTED_TRACING_BASE_URL:
      http://distributed-tracing:8000` to the `api-gateway` service's
      `environment:` block (one line, same as `LOGGING_BASE_URL`)
- [x] No changes to `proxy_router.py` / `proxy_service.py` — the existing
      catch-all proxy already handles any registered route

## Phase 10 — Infra wiring

- [x] `docker-compose.yml` — new service block (name it `distributed-tracing`
      to match the gateway env var above; container_name
      `backendservicekit-distributedtracing`): `build:
      ./services/DistributedTracing`, `ports: ["8007:8000"]` (next free host
      port — 8001–8006 are taken), `environment: TEMPO_BASE_URL=http://tempo:3200`,
      same `backend` network, **no `profiles:` restriction and deliberately
      no `depends_on: tempo`** (see Decision #7 — tempo sits behind
      `observability`; a hard `depends_on` would break `docker compose up`
      without that profile)
- [x] Confirm `tempo`'s port 3200 stays reachable only inside the `backend`
      network from this service — no host-mapping change needed, it's
      already `3200:3200` for local Grafana/dev use, which is fine to leave
      as-is (unlike Loki, this is a read-only query port with no ingestion
      risk if left reachable)

## Phase 11 — Testing

- [x] Unit tests for `trace_repository.py` TraceQL construction (given
      filters → expected query string) — no real Tempo needed (mirrors
      `services/Logging/tests/unit/test_log_repository.py`)
- [x] Unit tests for `require_operator_scope` (reject non-admin, allow
      `platform-admin`) — simpler than Logging's tenant-scope tests since
      there's only one tier for v1
- [ ] Integration tests against a real `tempo` test container for
      `/traces/{id}`, `/traces/search`, `/traces/export` — same
      testcontainers approach Logging deferred (tracked there as a
      not-yet-done item); consider doing both services' testcontainers work
      in the same pass since the fixture setup will be near-identical
- [x] Before writing any test that asserts on OTel span JSON shape, actually
      build the Docker image and run it against a real Tempo container the
      way Logging's rollout did — that's what caught the `shared/`
      not-in-build-context issue and the two Dockerfile bugs listed in
      `services/Logging/TODO.md`'s Implementation Notes. Assume this
      service's Dockerfile has the same class of problem until proven
      otherwise by actually building it, even though Phase 1 says to copy
      Logging's already-fixed Dockerfile.
- [ ] `task test SERVICE=DistributedTracing` wired into root `Taskfile.yml`
      service list once `pyproject.toml` exists

## Explicitly Out of Scope for v1

- Changing anything about how Tenent or APIGateway emit spans (including the
  likely-dead-code manual tracer setup noted in Decision #1 — real, but not
  this service's job to fix)
- Wiring `set_tenant_span_attributes()` into Tenent/APIGateway so trace data
  actually carries `tenant_id` (Decision #3) — until that happens, this
  service is operator-only, not tenant-self-service
- A second datastore for traces — Tempo stays the only store
- An ingestion endpoint (Decision #5) — otel-collector's OTLP HTTP receiver
  already covers that need correctly
- Per-trace delete as a real guarantee (Decision #4 / Phase 6)
- Fixing Prometheus's missing `--web.enable-remote-write-receiver` flag so
  Tempo's `metrics_generator` push actually lands (Decision #2) — noted so
  nobody builds a metrics-backed dashboard endpoint assuming it's populated
- Async export workers — same backlog note as Logging's Phase 7
- mTLS / advanced gateway hardening — inherits whatever APIGateway/Kong
  decide for all upstreams (see `services/APIGateway/TODO.md`)

## Implementation Notes (found while building, not obvious from the plan)

1. **`services/DistributedTracing/tempo/tempo.yml` had a real bug — Tempo
   could not start at all with the config as originally checked in.** The
   top-level `metrics_generator:` block had a `processors: [service-graphs,
   span-metrics]` key. That field does not exist on `generator.Config` in
   Tempo 2.5.0 — it only exists nested under `overrides.defaults.metrics_generator`
   (which the file already had, correctly, further down). With the
   duplicate top-level key present, `grafana/tempo:2.5.0` fails config
   parsing and exits immediately: `failed parsing config: ... field
   processors not found in type generator.Config`. This was only caught by
   actually starting a real Tempo container with this exact file (`docker
   run ... -v .../tempo.yml:/etc/tempo/tempo.yml:ro`) — `docker compose
   config` and reading the YAML would never have surfaced it. Fixed by
   deleting the invalid top-level key and leaving a comment explaining why
   it can't come back. This is squarely in this service's own scope (the
   file lives under `services/DistributedTracing/`), not a Tenent/APIGateway
   change, so fixing it directly was appropriate rather than just noting it.

2. **Tempo's two trace-fetching endpoints encode span/trace ids
   differently — verified by pushing a real span via OTLP and reading both
   responses back.** `GET /api/search` returns `traceID` / `spanID` as plain
   hex strings (e.g. `"5b0088c27869ca26"`). `GET /api/traces/{id}` returns
   the same span's `spanId` / `parentSpanId` **base64-encoded**
   (`"WwCIwnhpyiY="` — standard OTLP-JSON encoding for a protobuf `bytes`
   field). These decode to the identical value
   (`base64.b64decode("WwCIwnhpyiY=").hex() == "5b0088c27869ca26"`), but
   without converting one to match the other, this service's `/traces/{id}`
   response would show a `span_id` that doesn't match what `/traces/search`
   or Tempo's own UI (Grafana/Jaeger) shows for the exact same span — making
   cross-referencing silently broken. Fixed in
   `app/repositories/trace_repository.py`'s `_decode_span_id()`, which
   base64-decodes and re-hex-encodes `spanId`/`parentSpanId`, falling back
   to the raw value if decoding fails (some other Tempo version, or
   already-hex input). Covered by
   `tests/unit/test_trace_repository.py::test_parse_trace_decodes_base64_span_ids_to_hex`
   and the router-level fixture in `test_traces_router.py`, both of which
   use the exact base64 string captured from the live container rather than
   a made-up placeholder — a placeholder like `"root"` turned out to itself
   be valid base64 (decodes to `ae8a2d`), which would have silently masked
   this exact bug if the fixture hadn't been checked against real output.

3. This service's own Dockerfile was copied from Logging's **already-fixed**
   version (correct `COPY pyproject.toml uv.lock ./` and no `uv run` wrapper
   in the runtime CMD — see `services/Logging/TODO.md`'s Implementation
   Notes for why those were bugs in the original Tenent-derived pattern).
   Built and ran the image against a real Tempo container to confirm no new
   issue was introduced by copying it — none was; it worked on the first
   build. Worth calling out that "copy the already-fixed file" only pays off
   if you actually verify it still works in the new context, not just trust
   the copy.
