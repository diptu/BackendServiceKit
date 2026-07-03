# Metrics Collection Service — TODO

**Status: Phases 1–11 implemented; Phase 12 partial.** See "Implementation
Notes" at the bottom — this build found two more real, pre-existing bugs
beyond what this plan anticipated (recording rules were never loaded by
Prometheus at all, independent of the metric-name issue), and Decision #6
is resolved below (skipped node-exporter for v1).

Same shape as `services/Logging/` and `services/DistributedTracing/` (both
implemented — see their `TODO.md`s for the concrete pattern: a thin FastAPI
query/API layer in front of a specialized backend, not a second ingestion
path and not a second datastore). This is the most tangled of the three
domains, though — Decisions #1, #4, #5 and #6 below are real, structural
differences from the other two, not just repeated boilerplate. Read all of
them before starting; don't assume "copy Logging" covers this one.

## Design Decisions (read first — these shape every phase below)

Discovered by inspecting the current stack (docker-compose.yml,
prometheus.yml, recording.yml, otelcol/config.yaml,
shared/observability/metrics/*, shared/observability/dashboards/*, Tenent's
app/core/metrics.py) before writing a single line:

1. **The existing metrics pipeline is not just unused, like Logging's
   formatter gap — it's actively self-inconsistent, and grep confirms it
   with certainty.** `grep -rn "shared.observability.metrics\|get_meter\|
   create_counter\|create_histogram\|RequestMetricsMiddleware" services/{Tenent,
   APIGateway,Logging,DistributedTracing}/app` returns **zero matches**.
   None of `shared/observability/metrics/registry.py` (OTel `MeterProvider`
   factory), `counters.py`/`histograms.py`/`gauges.py` (OTel metric
   constructors), or `middleware.py` (`RequestMetricsMiddleware`, a
   *separate*, non-OTel, `prometheus_client`-based RED-metrics middleware)
   is ever imported anywhere. Consequences, each verified by reading the
   actual config, not assumed:
   - `otel-collector`'s `metrics` pipeline (`receivers:[otlp] → ... →
     exporters:[prometheus]` on `:8889`, namespace `nutratenant`) receives no
     real application data points today, because nothing anywhere calls the
     OTel Metrics SDK. `prometheus.yml`'s `otel-collector` scrape job is
     scraping an effectively-empty endpoint for app metrics.
   - `recording.yml`'s six rules all query `nutratenant_http_requests_total`,
     `nutratenant_http_request_duration_seconds_bucket`,
     `nutratenant_isolation_decisions_total`, or
     `nutratenant_isolation_violations_total` — metric names that only exist
     if the OTel pipeline above were populated. **They evaluate to empty
     results today.** Prometheus does not error or alert when a recording
     rule matches nothing; this fails completely silently.
   - `shared/observability/dashboards/request_metrics.json` queries
     `http_requests_total` (no `nutratenant_` prefix — assumes
     `RequestMetricsMiddleware` were wired in and scraped directly). Also
     dead, and inconsistent with recording.yml's own naming assumption —
     these two already-checked-in artifacts don't even agree with each
     other about what the metric would be called if it existed.
   - The one thing that *does* work: Tenent's own `app/core/metrics.py`
     defines five hand-rolled `prometheus_client` metrics
     (`isolation_decisions_total`, `isolation_violations_total`,
     `isolation_resource_claims_total`, `isolation_active_policies`,
     `isolation_check_duration_seconds`) on its own local `CollectorRegistry`,
     mounted at `/metrics`, and `prometheus.yml`'s `tenent` direct-scrape job
     picks it up — **under its real, unprefixed names**, not the
     `nutratenant_`-prefixed ones recording.yml queries. APIGateway has no
     equivalent local metrics module at all — its `/metrics` (mounted with
     bare `make_asgi_app()`, the default global registry) exposes only
     `prometheus_client`'s automatic process/platform collectors, nothing
     application-specific.

   **This service must query for what's real** (`job="tenent"` scraped
   series under their actual unprefixed names; default process metrics for
   `job="api-gateway"`), not build on the assumption that the OTel pipeline
   or the dashboard's naming convention are populated. Phase 8 below fixes
   `recording.yml` and the dashboard directly — both are config/data
   artifacts this service owns or is closely coupled to, not Tenent/
   APIGateway application code, so fixing the names is in scope (same
   reasoning that made fixing `tempo.yml`'s bug in-scope for
   DistributedTracing). **Do not** wire `shared.observability.metrics` into
   Tenent/APIGateway to make the old names real instead — that's an edit to
   those services' own code, out of scope here (see Decision #7).

2. **Prometheus is the system of record. This service does not duplicate
   storage** for scraped/pulled metrics. It is a query/API layer over
   Prometheus's HTTP API: `GET /api/v1/query`, `GET /api/v1/query_range`,
   `GET /api/v1/series`, `GET /api/v1/label/<name>/values`,
   `GET /api/v1/labels`, `GET /-/ready`. (Pushed metrics are a partial
   exception — see Decision #4.)

3. **No tenant-isolation label exists on any real metric today** — same
   shape as DistributedTracing's Decision #3, for the same underlying
   reason. Tenent's `isolation_decisions_total` Counter is labeled only
   `["decision"]` — no `tenant_id`. **This service defaults to operator /
   platform-admin-only access for v1**, not tenant self-service. A
   `tenant_id` label-matcher filter is still built into the PromQL query
   builder (Phase 4) as a forward-compatible no-op, exactly like
   DistributedTracing's `tenant_id` TraceQL filter — it starts working the
   moment someone adds that label to a real metric in Tenent/APIGateway,
   which is out of scope here.

4. **Prometheus is fundamentally pull-based — `POST /metrics` /
   `POST /metrics/bulk` cannot be "just an ingestion escape hatch" the way
   Logging's `POST /logs` was, and this is a real architectural fork from
   both prior services.** There is no way to push an arbitrary one-off
   metric point into Prometheus's own storage directly. The standard,
   correct Prometheus-ecosystem answer for short-lived/batch processes that
   can't be scraped (and this stack already has some: `api-gateway-worker`
   and the TenantProvisioning Celery workers run with no HTTP server to
   scrape) is **Pushgateway** — a small, purpose-built companion component
   (`prom/pushgateway`), not something to reimplement in this app. Design:
   `POST /metrics` / `/metrics/bulk` validate the README's JSON shape
   (`{"metric": "cpu_usage", "value": 67, "timestamp": "..."}`), translate
   it into Prometheus text-exposition format, and `PUT`/`POST` it to
   Pushgateway's `/metrics/job/<job>/...` grouping endpoint. Pushgateway
   itself then becomes one more Prometheus scrape target (Phase 11). This
   keeps the "no duplicate storage" rule intact — Pushgateway *is* the
   store for pushed data, this service still isn't.

   Known Pushgateway gotcha worth documenting up front: pushed metrics
   persist **until explicitly deleted or Pushgateway restarts** — there is
   no TTL. A pushed gauge from a job that stopped running an hour ago will
   keep reporting its last value as "current" forever unless something
   deletes it. This is exactly why Decision #5's `DELETE /metrics` isn't
   just a nice-to-have here the way it was aspirational for Logging/Tracing
   — it's operationally necessary for anything pushed through this service.

5. **`DELETE /metrics` is partially real — genuinely different from
   Logging's and DistributedTracing's "always 501" answer.** Pushgateway
   supports a real `DELETE /metrics/job/<job>[/<label>/<value>...]` that
   removes previously-pushed series for that grouping — this is fully
   supported, not aspirational, *for data that arrived via this service's
   own push path*. Deleting arbitrary *scraped* (pull-based) series is a
   different story: Prometheus's TSDB delete API
   (`DELETE /api/v1/admin/tsdb/delete_series`) requires
   `--web.enable-admin-api` (not set on the `prometheus` compose service,
   and a genuinely dangerous flag to add casually — it also enables
   snapshot/shutdown admin endpoints). Design: `DELETE /metrics/{job}`
   proxies to Pushgateway and actually works. A bare `DELETE /metrics`
   with no job scope, or one that resolves to scraped (non-pushed) data,
   returns `409` explaining the distinction — not a blanket `501` like the
   other two services, because part of this actually works.

6. **`GET /metrics/system` (the README's "CPU Usage"/"Memory" examples) has
   no data source today.** No `node-exporter` or `cAdvisor` is deployed
   anywhere in `docker-compose.yml` (confirmed — full container list has
   none). Decide before building Phase 5: either (a) add a lightweight
   `node-exporter` (host-level) — cheap, standard, one more compose service
   behind the `observability` profile — and scope `/metrics/system` to what
   it exposes, or (b) skip real system metrics for v1 and scope the
   endpoint down to whatever Prometheus's own self-scrape/process metrics
   already offer (`job="prometheus"`, `job="otel-collector-internal"`) —
   much less useful, but zero new infra.

   **Resolved: (b).** Implemented as a query for
   `process_resident_memory_bytes` / `process_cpu_seconds_total` across
   whatever jobs expose them — no job filter, so coverage is whatever it is.
   Verified against a real Prometheus + Pushgateway: turns out **every**
   Go binary using the standard Prometheus client library (Prometheus and
   Pushgateway themselves, in addition to any of this stack's own
   default-registry FastAPI services) exposes these automatically, so the
   endpoint returns real, non-trivial data with zero extra infra — better
   coverage than expected going in. Tenent still won't appear (its own bare
   `CollectorRegistry` doesn't auto-register `ProcessCollector`), which is
   fine and documented on the endpoint itself. Adding node-exporter/cAdvisor
   for genuine host-level metrics remains a legitimate future upgrade, not
   done here — don't silently fake that data in the meantime.

7. **Every touch to Tenent/APIGateway is additive, one line** — same
   `Route(...)` / enum member / config field pattern used for Logging and
   DistributedTracing in APIGateway's `RouteService`. Unlike those two
   services, though, **there is no ingestion-side touch needed at all** —
   `prometheus.yml` already has direct-scrape jobs for `tenent` and
   `api-gateway` (Decision #1), so pull-based ingestion already works
   end-to-end with zero code changes anywhere, exactly the property Logging
   and DistributedTracing also rely on for their respective backends.

8. **Prometheus sits behind the `observability` compose profile** (same as
   `loki` and `tempo`). No hard `depends_on: prometheus` for the new
   service — same graceful-degradation-via-`/ready` pattern used for both.

---

## Phase 1 — Scaffold (no business logic)

- [x] Create `services/MetricsCollection/app/` mirroring
      `services/Logging/app/`'s Enterprise Clean Architecture layout:
      `api/v1/`, `core/`, `domain/`, `infrastructure/`, `repositories/`,
      `schemas/`, `services/`, `middleware/` (no `models/`)
- [x] `pyproject.toml` + `uv.lock` — copy `services/Logging/pyproject.toml`
      verbatim as a base (same deps)
- [x] `app/core/config.py` — `Settings`: `PROMETHEUS_BASE_URL` (default
      `http://localhost:9090`), `PROMETHEUS_TIMEOUT`, `PUSHGATEWAY_BASE_URL`
      (default `http://localhost:9091`), `SECRET_KEY`, `JWT_AUTH_ENABLED`,
      `JWT_ALGORITHM`, `ENVIRONMENT`, `CORS_ALLOW_ORIGINS`
- [x] `app/core/logging.py` — copy `services/Logging/app/core/logging.py`
      verbatim (best-effort `shared.observability` import, local fallback —
      see that file's docstring; same constraint applies here)
- [x] `app/main.py` — FastAPI app factory, lifespan startup: build shared
      `httpx.AsyncClient`s for Prometheus and Pushgateway, wire OTel per the
      established try/except resilience pattern
- [x] `app/api/v1/health_router.py` — `/health` (liveness) + `/ready`
      (readiness probe: `GET {PROMETHEUS_BASE_URL}/-/ready`)
- [x] `Dockerfile` — copy `services/Logging/Dockerfile` **exactly**
      (already has both fixes over the original Tenent-derived pattern —
      correct `COPY pyproject.toml uv.lock ./`, no `uv run` wrapper in the
      runtime CMD)
- [x] `.env.example`, `.dockerignore`
- [x] `scripts/lint.sh`, `scripts/fix.sh` (copy from Logging, no changes needed)

## Phase 2 — Prometheus + Pushgateway clients (no business logic)

- [x] `app/infrastructure/prometheus/prometheus_client.py` — async httpx
      wrapper: `instant_query(promql, time)` → `GET /api/v1/query`,
      `range_query(promql, start, end, step)` → `GET /api/v1/query_range`,
      `label_values(name)` → `GET /api/v1/label/{name}/values`,
      `metric_names()` → `label_values("__name__")`, `ready()` →
      `GET /-/ready`. No business logic — raw PromQL in, raw parsed JSON out
      (mirrors `services/Logging/app/infrastructure/loki/loki_client.py`
      and `services/DistributedTracing/.../tempo_client.py` structure).
- [x] `app/infrastructure/pushgateway/pushgateway_client.py` — `push(job,
      grouping_labels, exposition_text)` → `POST /metrics/job/<job>/...`,
      `delete(job, grouping_labels)` → `DELETE /metrics/job/<job>/...`. Only
      knows Pushgateway's grouping-key URL scheme and the text-exposition
      wire format — no metric-shape validation here (see Phase 6).
- [x] `app/domain/exceptions.py` — `PrometheusUnavailableError`,
      `PrometheusQueryError`, `InvalidPromQLError`,
      `PushgatewayUnavailableError`, `PushgatewayError`,
      `ScrapedMetricDeleteNotSupportedError` (see Decision #5)
- [x] `app/domain/metric.py` — internal dataclasses: `MetricSample`
      (metric_name, labels: dict, value, timestamp_s) and `MetricSeries`
      (metric_name, labels, values: list[tuple[timestamp_s, value]] — for
      range-query results)
- [x] `app/repositories/metric_repository.py` — translates filter args
      (metric_name, job/service, tenant_id, label matchers) into a PromQL
      selector string; parses Prometheus's `/api/v1/query` and
      `/api/v1/query_range` response shapes (`data.resultType` of `vector`,
      `matrix`, or `scalar` — handle all three, Prometheus returns different
      shapes depending on the query) into `MetricSample`/`MetricSeries`
      objects. This is the *only* place PromQL syntax is constructed (same
      rule Logging/DistributedTracing apply to LogQL/TraceQL).

## Phase 3 — Access control (operator-only — see Decision #3)

- [x] `app/middleware/auth.py` — copy verbatim from Logging/DistributedTracing
- [x] `app/api/v1/dependencies.py` — `require_operator_scope()`, copied from
      `services/DistributedTracing/app/api/v1/dependencies.py` almost
      verbatim (same uniform single-tier model, same reasoning)

## Phase 4 — Read API

- [x] `GET /api/v1/metrics` — list known metric names via
      `metric_names()`, optionally filtered by a `prefix`/`contains` query
      param (there is no single reliable prefix across this stack per
      Decision #1, so don't hardcode `nutratenant_`)
- [x] `GET /api/v1/metrics/query` — instant PromQL query built from
      `metric` (required), `job`/`service`, `tenant_id` (no-op, see
      Decision #3), and arbitrary `label:value` pairs via a `q` param
      (same `key=value[,key2=value2]` convention DistributedTracing uses)
- [x] `GET /api/v1/metrics/history` — range query: same filters plus
      `start`, `end`, `step` (default step: something sane like 60s) —
      proxies `range_query()`
- [x] `GET /api/v1/metrics/service/{service}` — thin wrapper over
      `/query`/`/history` with `job="{service}"` fixed (the real,
      always-present Prometheus label — **not** `service.name`, which only
      exists on the dead OTel pipeline per Decision #1)
- [x] `app/schemas/metric.py` — `MetricSampleResponse`, `MetricSeriesResponse`,
      `MetricListResponse`, `MetricQueryResponse`

## Phase 5 — Derived views

- [x] `GET /api/v1/metrics/top` — `topk(<n>, <metric>)` PromQL, generic,
      `n` and `metric` as query params
- [x] `GET /api/v1/metrics/tenant/{tenant}` — forward-compatible no-op
      filter wrapper, same as DistributedTracing's `/traces` tenant_id
      handling — documented in OpenAPI as currently a no-op (Decision #3)
- [x] `GET /api/v1/metrics/system` — **resolve Decision #6 first.** If
      going with node-exporter: wrapper over standard `node_cpu_seconds_total`
      / `node_memory_*` queries. If skipping: wrapper over whatever
      self-scrape process metrics exist, clearly documented as limited.
      Do not build this endpoint before the decision is made — it's the one
      place a wrong assumption would produce plausible-looking fake data.

## Phase 6 — Push ingestion via Pushgateway (see Decision #4 — real architecture fork from Logging)

- [x] `app/schemas/metric.py` — `MetricPushCreate` (metric: str, value:
      float, job: str, labels: dict[str, str] = {}, metric_type: "gauge" |
      "counter" = "gauge") — README's example omits `job`/grouping, but
      Pushgateway requires one; default it to a generic value like
      `"external"` if the caller doesn't supply one, don't reject the
      request
- [x] `app/services/metric_ingest_service.py` — builds Prometheus
      text-exposition format from `MetricPushCreate` (`# TYPE <name>
      <type>\n<name>{labels} <value>\n`), calls
      `pushgateway_client.push(job, labels, text)`
- [x] `POST /api/v1/metrics` — single metric push (escape hatch, operator-gated)
- [x] `POST /api/v1/metrics/bulk` — batch push, same `max_items` cap
      pattern as Logging's `/logs/bulk`
- [x] Document explicitly in the OpenAPI description: this path writes to
      Pushgateway, a **separate store from scraped metrics** — a pushed
      `cpu_usage` gauge and a scraped one with the same name are not the
      same series and won't merge

## Phase 7 — `DELETE /metrics/{job}` (implement the real, scoped support from Decision #5)

- [x] `DELETE /api/v1/metrics/{job}` — proxies to
      `pushgateway_client.delete(job, grouping_labels)`. Works for real,
      for pushed data.
- [x] `DELETE /api/v1/metrics` (no job) — `409`, explaining that
      Prometheus's own scraped series can't be deleted this way
      (`--web.enable-admin-api` isn't enabled and isn't being enabled for
      this), and that a job-scoped delete only removes pushed data (see
      Decision #5). This is a real behavioral difference from Logging's and
      DistributedTracing's flat `501` — don't copy those verbatim here.

## Phase 8 — Fix the already-broken metrics artifacts (in-scope config/data fixes, not app code)

- [x] `services/MetricsCollection/prometheus/rules/recording.yml` — repointed
      the two isolation rules at the real, unprefixed names Tenent actually
      exports (`isolation_decisions_total{job="tenent"}`,
      `isolation_violations_total{job="tenent"}`). The `nutratenant.http.rate5m`
      group (four rules querying `nutratenant_http_requests_total` /
      `nutratenant_http_request_duration_seconds_bucket`) was **deleted
      outright**, not repointed — there is no HTTP RED-metrics source under
      any name anywhere in this stack today (Tenent's own metrics module
      only covers the isolation domain; APIGateway has no custom metrics at
      all), so scoping the old rules to `job="tenent"` would still be querying
      a metric that doesn't exist. Verified by loading the fixed file into a
      real Prometheus container and checking `/api/v1/rules` — both
      remaining rules parse and appear with no config errors.
- [x] Found a second, independent bug while doing this: `prometheus.yml`'s
      `rule_files` only globbed `/etc/prometheus/alerts/*.yml` — `recording.yml`
      was mounted into the container by `docker-compose.yml` but never
      referenced by `rule_files` at all, so it was **never loaded into
      Prometheus**, independent of the metric-name problem above. Fixed by
      adding `/etc/prometheus/rules/*.yml`. Verified the same way — real
      Prometheus container, `/api/v1/rules` now actually lists both rules
      (it returned an empty group list before this fix, even after the
      metric-name fix, which is what surfaced the bug).
- [x] All four files in `shared/observability/dashboards/` were checked —
      turned out worse than this plan assumed going in. `database_metrics.json`,
      `api_latency.json`, and `request_metrics.json` have **no real metric
      under any name** to fix their queries to — Tenent/APIGateway don't
      instrument HTTP/DB/cache operations with any metrics library at all,
      so "repoint to the real name" isn't possible for these three; a
      rename would just be a different-looking broken query. Fixed by adding
      a top-level `description` field to each explaining plainly that no
      panel has real data today and why, rather than pretending a rename
      solves it. `redis_metrics.json` got the same treatment for its first
      three panels, but its fourth panel (`isolation_decisions_total`) *is*
      real — added `job="tenent"` to that query for precision and renamed
      the panel title to flag it as the one working panel in an otherwise
      broken dashboard, left in place rather than relocated to a
      differently-named file (that would be scope creep for a cleanup pass).

## Phase 9 — Observability for the service itself

- [x] Dogfood `shared/observability`: `configure_logging()`, OTel tracing,
      `/metrics` via `prometheus_client` — same as Logging/DistributedTracing.
      Add this service's own scrape job in Phase 11 so it doesn't end up in
      the same "exposes /metrics, nobody scrapes it" state Logging and
      DistributedTracing are currently in (see Phase 11).
- [x] Custom counters: `metrics_query_total{status}`,
      `metrics_query_duration_seconds`, `metrics_push_total`,
      `metrics_delete_total`

## Phase 10 — Gateway integration (additive only — APIGateway changes)

- [x] `services/APIGateway/app/domain/enums.py` — add one
      `UpstreamService.METRICS_COLLECTION` member
- [x] `services/APIGateway/app/core/config.py` — add one
      `metrics_collection_base_url: str` setting
- [x] `services/APIGateway/app/services/route_service.py` — add one
      `Route(prefix="/api/v1/metrics", upstream=UpstreamService.METRICS_COLLECTION,
      cacheable_methods=frozenset(), cache_ttl=0)` entry — not cacheable,
      same reasoning as `/api/v1/logs` and `/api/v1/traces`
- [x] `services/APIGateway/app/services/kong_admin_service.py` —
      `KONG_ROUTE_PREFIX_MAP` gets one more entry:
      `"/api/v1/metrics": "nutratenant-metrics-collection"`
- [x] Update every APIGateway test that asserts an exact route count —
      by now this is a known, recurring checklist (bit us on both Logging
      and DistributedTracing): `test_route_service.py` (registered count,
      resolve-by-upstream count), `test_gateway_router.py` (routes total,
      prefix set, cacheable-methods/cache-ttl per-route checks, **and** the
      unique-upstreams-probed count in
      `test_gateway_status_probes_unique_upstreams_only` — easy to miss,
      found it twice already), `test_kong_admin_service.py` (sync counts),
      `test_proxy_router.py` (gateway routes total). Grep the whole
      `tests/` tree for the current route count as a literal integer before
      declaring this phase done, don't rely on remembering which files had
      it last time.
- [x] `docker-compose.yml` — add `METRICS_COLLECTION_BASE_URL:
      http://metrics-collection:8000` to the `api-gateway` service's
      `environment:` block

## Phase 11 — Infra wiring

- [x] `docker-compose.yml` — new `metrics-collection` service block:
      `build: ./services/MetricsCollection`, `ports: ["8008:8000"]` (next
      free host port — 8001–8007 are taken), `environment:
      PROMETHEUS_BASE_URL=http://prometheus:9090,
      PUSHGATEWAY_BASE_URL=http://pushgateway:9091`, same `backend` network,
      **no `profiles:` restriction and deliberately no `depends_on:
      prometheus`** (see Decision #8)
- [x] `docker-compose.yml` — new `pushgateway` service block:
      `image: prom/pushgateway`, no host port needed (internal-only, talked
      to via this service), same `backend` network, behind the
      `observability` profile (it's a metrics-storage component, same
      category as loki/tempo/prometheus itself)
- [x] `services/MetricsCollection/prometheus/prometheus.yml` — add scrape
      jobs for: `pushgateway:9091` (`honor_labels: true` — required so
      Pushgateway doesn't overwrite the pushed job/instance labels with its
      own), `logging:8000/metrics`, `distributed-tracing:8000/metrics`, and
      this new `metrics-collection:8000/metrics` — all four are currently
      either unscraped (Logging, DistributedTracing — a real gap, found
      while writing this plan) or don't exist yet (Pushgateway,
      metrics-collection itself)
- [x] Resolve Decision #6 (node-exporter/cAdvisor) and add that compose
      service too if going that route, plus its own `prometheus.yml` scrape job
- [x] Confirm `prometheus`'s port 9090 exposure is unchanged — it's a
      read-only query port like Tempo's, not a write path, so leaving
      `9090:9090` mapped for local Grafana/dev use is fine as-is

## Phase 12 — Testing

- [x] Unit tests for `metric_repository.py` PromQL construction (given
      filters → expected query string) and response parsing for all three
      Prometheus result types (`vector`, `matrix`, `scalar`) — no real
      Prometheus needed
- [x] Unit tests for `require_operator_scope` — copy the shape of
      DistributedTracing's `test_operator_scope.py`
- [x] Unit tests for the Pushgateway text-exposition format builder — given
      a `MetricPushCreate`, assert the exact wire text produced
- [ ] Integration tests against real `prometheus` and `pushgateway`
      containers for `/metrics/query`, `/metrics/history`, `POST /metrics`
      round-tripped through a `GET`, and `DELETE /metrics/{job}` actually
      removing what was pushed — same testcontainers work Logging and
      DistributedTracing both deferred; this is now the third service with
      the same deferred item, worth doing as one shared effort across all
      three rather than three separate ad-hoc setups
- [x] Before trusting any Prometheus response-parsing code, actually build
      the Docker image and run it against a real `prometheus` (and
      `pushgateway`) container the way both prior services did — that
      discipline caught a real base64/hex encoding mismatch in
      DistributedTracing and a fatal config bug in Tempo's own YAML.
      Prometheus's `resultType`-dependent response shape (Phase 2) is
      exactly the kind of thing that looks right on paper and is subtly
      wrong in practice — verify it before believing the parser is correct.
- [ ] `task test SERVICE=MetricsCollection` wired into root `Taskfile.yml`
      service list once `pyproject.toml` exists

## Explicitly Out of Scope for v1

- Wiring `shared.observability.metrics` (OTel Metrics SDK) into Tenent/
  APIGateway to make the `nutratenant_`-prefixed names in the old
  recording.yml real instead of fixing the names to match reality (Decision
  #1) — that's an edit to those services' own code
- Adding a `tenant_id` label to any real metric in Tenent/APIGateway
  (Decision #3) — until that happens, this service is operator-only
- A second datastore for scraped metrics — Prometheus stays the only store
  for pull-based data (Pushgateway is the store for pushed data, which is a
  real, separate, already-standard component — not duplication)
- Deleting arbitrary scraped series via `--web.enable-admin-api` (Decision #5)
- Async export workers / a `POST /metrics/export` — the README doesn't ask
  for one and Prometheus's own `/api/v1/query_range` already covers bulk
  historical reads reasonably well through `/metrics/history`
- mTLS / advanced gateway hardening — inherits whatever APIGateway/Kong
  decide for all upstreams (see `services/APIGateway/TODO.md`)

## Implementation Notes (found while building, not obvious from the plan)

1. **`prometheus.yml`'s `rule_files` never loaded `recording.yml` at all —
   a bug independent of, and more fundamental than, the metric-name problem
   this plan already knew about.** It only globbed
   `/etc/prometheus/alerts/*.yml`; `docker-compose.yml` mounts
   `recording.yml` into `/etc/prometheus/rules/`, a directory `rule_files`
   never referenced. This means the recording rules had never been
   evaluated by Prometheus even once, regardless of whether their metric
   names were correct. Only caught by actually loading the config into a
   real Prometheus container and checking `/api/v1/rules` came back empty
   even after the metric-name fix — reading the YAML alone would not have
   surfaced this, since both files individually look reasonable. Fixed by
   adding the missing glob.

2. **Three of the four Grafana dashboards have no real fix available at
   all, not just a naming mismatch** — this plan's Decision #1 assumed a
   rename would fix them; building the service revealed there's no
   equivalent real metric under *any* name for HTTP/DB/cache RED metrics,
   because Tenent/APIGateway simply don't instrument those domains with any
   metrics library. Documented plainly in each dashboard's JSON rather than
   silently "fixing" a query to point at a name that still doesn't exist.

3. **Decision #6 (system metrics) resolved better than expected.** Went
   with skipping node-exporter for v1 and querying
   `process_resident_memory_bytes` / `process_cpu_seconds_total` with no
   job filter. Verified against a real Prometheus + Pushgateway: both are
   themselves Go binaries using the standard Prometheus client library, so
   they show up automatically — the endpoint returns real data with zero
   extra infrastructure, better coverage than anticipated when this
   decision was first written as "open."

4. **Full push → Pushgateway → real Prometheus scrape → query → delete →
   re-scrape round trip was verified end-to-end**, not just unit-tested:
   pushed a `cpu_usage` gauge through `POST /metrics`, waited for a real
   scrape interval, queried it back through `/metrics/query` (confirming
   the value and labels survived the round trip through actual Prometheus
   text-exposition parsing), then deleted it through `DELETE /metrics/{job}`
   and confirmed — after another scrape interval — that it was genuinely
   gone rather than just hidden. This is exactly the kind of thing Phase 12
   flagged as "looks right on paper, verify it's actually right in
   practice," and this time it was — no bugs found in the push/delete path
   itself, unlike the base64/hex issue DistributedTracing's equivalent
   check caught.

5. This service's own Dockerfile was copied from Logging's already-fixed
   version verbatim and built clean on the first try — no new issues, same
   as DistributedTracing's experience copying the same file.
