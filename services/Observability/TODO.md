# Observability Service — TODO

**Status: FastAPI service implemented — app, sibling clients, topology
mining, five composition services, all 10 endpoints, 55 tests, additive
APIGateway + docker-compose + Prometheus wiring all done.** The one phase
that could not be completed is real-container verification against the six
actual sibling services (Phase 12's last item) — see Implementation Notes
at the bottom for what was verified instead, and why.

**Important pre-condition, read first:** this design composes six sibling
services — `Logging`, `DistributedTracing`, `MetricsCollection`,
`Monitoring`, `Alerting`, `HealthCheck` — all of which were fully
implemented earlier in this project's history but, as of this writing, exist
on disk only as their original `README.md` design docs again (their
implementations were lost to an out-of-band branch switch that discarded
uncommitted work, unrelated to this task). This service's sibling clients
(Phase 2) are written against those services' *established designs* (their
own `TODO.md` Decisions, which this document cites by name throughout) as
the source of truth for what each one's real API surface is — except
Alerting's and HealthCheck's, whose exact schemas are quoted verbatim from
memory in `alerting_client.py`/`health_client.py`'s own docstrings, since
those two were fresh enough in context to transcribe precisely rather than
reconstruct. All six need to exist and be running before Phase 12's final
real-container verification step can happen — that rebuild is tracked
separately, not part of this document.

## Why this is the hardest "which tier" call yet

Every prior service in this series had to answer "what's the one genuinely
new thing this adds, and what do I compose instead of re-implementing?"
This one has to answer that question **six times over**, against every
other service already built, plus fight off a real risk: the README's own
example diagram (`Apps → Logging/Metrics/Tracing/HealthCheck → Monitoring →
Alerting → Observability`) puts this at the very top, meaning it's tempting
to treat it as "Monitoring, but bigger" or "HealthCheck, but bigger" and
just re-expose their data with a new URL prefix. Read Decision #1 before
anything else — it's what keeps this from being that.

## Design Decisions (read first — these shape every phase below)

1. **This is a fourth tier: an investigation/correlation layer over
   everything below it, never a bypass of any of it.** The stack so far:
   tier 1 (raw backends: Loki, Tempo, Prometheus, Alertmanager,
   Pushgateway), tier 2 (per-domain query services: Logging over Loki,
   DistributedTracing over Tempo, MetricsCollection over Prometheus), tier 3
   (cross-cutting composers, each with one specific job: Monitoring —
   service reachability/topology; Alerting — alert lifecycle; HealthCheck —
   per-service `/ready` shape normalization). Observability is tier 4: it
   composes tier 2 and tier 3's REST APIs to answer investigation questions
   ("why did this happen?") that need *content* from more than one domain at
   once — a single log line, correlated with a trace, correlated with a
   metric, correlated with whether an alert fired. It must never call
   Loki/Tempo/Prometheus/Alertmanager directly (that's re-litigating
   Decision #1 from three prior services' TODOs) and must never re-probe
   service reachability (that's Monitoring's job) or re-normalize `/ready`
   shapes (that's HealthCheck's job) — it calls *their* already-built
   endpoints, the same "compose, don't duplicate" rule every tier-3 service
   in this series has followed relative to tier 1/2.

2. **`GET /observability/dependencies` sounds identical to HealthCheck's
   `GET /health/dependencies` and must not be.** HealthCheck's endpoint
   answers "is each service's *own* dependency (its database, its cache)
   up or down" — a health-status view. This service's `/dependencies`
   answers a structurally different question: "which services actually
   *call* which other services" — a **service call graph**, mined from
   real data DistributedTracing already has (span `parent_id`/`service.name`
   relationships across a trace) rather than static config or guesswork.
   Nothing in this repo exposes an actual observed service topology today;
   this is genuinely new, not a renamed copy of HealthCheck's endpoint. The
   naming collision with the README's own wording is worth flagging in the
   OpenAPI description so nobody confuses the two at the client level.

3. **`GET /observability/topology` is Decision #2's graph *plus* live
   health overlaid per node** — call `HealthCheck`'s `/health/dependencies`
   (or `/health/live`) for each node's current status and merge it onto the
   edges derived from trace data. This is the one endpoint that's
   legitimately "compose two tier-3 services' outputs into a third shape,"
   which is fine — Decision #1's rule is about not *duplicating* another
   service's internal logic, not about never calling two of them in the
   same request.

4. **`GET /observability/dashboard` composes five services' existing
   summary-shaped endpoints into one payload — it computes nothing new
   itself.** Concretely: `Logging`'s search API filtered to `level=error`
   over a recent window (count only), `MetricsCollection`'s system-metrics
   endpoint for headline numbers, `DistributedTracing`'s search API
   filtered to error/slow traces (count + top offenders),
   `HealthCheck`'s `/health/dependencies` for fleet health, and
   `Alerting`'s `/alerts` for the active/unsilenced count. Real,
   additive value: nobody today shows all five in one response — Monitoring's
   own `/monitoring/dashboard` is topology/tenant/resource-shaped, not
   log/trace/metric-*content*-shaped, so this isn't a duplicate of that
   either.

5. **`GET /observability/search` is a federated search, not a new query
   engine.** Accepts a free-text term and an optional time range;
   dispatches concurrently to `Logging`'s `/logs/search` (LogQL-backed) and
   `DistributedTracing`'s `/traces/search` (TraceQL-backed), merges results
   into one ranked/time-ordered list tagged by source (`log` vs `trace`).
   Metrics are deliberately excluded from this specific endpoint — PromQL
   isn't a free-text search surface the same way, and forcing it into this
   shape would be exactly the kind of "pretend two different things are the
   same" mistake HealthCheck's Decision #1 was written to avoid. Metric
   content shows up in `/dashboard` and `/correlation` instead, where a
   time-range + label query makes sense.

6. **`GET /observability/incidents` is a read-only reshaping of
   `Alerting`'s existing `/alerts` list — not a second incident-tracking
   datastore.** Groups active, non-silenced alerts (Alerting's own
   `status.state == "active"`, per its Decision #2) into an "incident" shape
   (grouped by `alertname`, with a first-seen time and affected-service
   list). No create/acknowledge/resolve endpoints here — those already
   exist on `Alerting`'s real API; duplicating them would violate the same
   "don't re-implement Alertmanager's real alert lifecycle" rule Alerting's
   own Decision #2 already established for itself.

7. **`GET /observability/root-cause` and `GET /observability/correlation`
   are the same underlying "gather correlated evidence for a
   service+time-window" engine, exposed two ways — and neither one does
   real causal inference.** A genuine root-cause/anomaly-correlation ML
   engine is out of scope for a v1 microservice in this repo — same
   honesty standard as every prior aspirational-vs-real gap in this series
   (Monitoring's nodes/clusters, Alerting's startup-probe, HealthCheck's
   startup-alias). What's real and buildable: given a `service` and a time
   window, concurrently pull that service's recent error logs (Logging),
   recent slow/failed traces (DistributedTracing), relevant metric samples
   (MetricsCollection), and any alerts that fired in that window
   (Alerting) — and return them side by side, time-aligned, with simple
   rule-based tags (e.g. "an alert fired in this window", "error rate above
   baseline"), not a computed verdict. `/root-cause` pre-fills the window
   around a specific alert or trace ID; `/correlation` takes an explicit
   service+window from the caller. Document plainly in the OpenAPI
   description that this is an evidence panel, not an automated diagnosis.

8. **`GET /observability/anomalies` is a simple, rule-based signal, not a
   statistics/ML anomaly-detection engine.** Real, bounded v1: surface
   `Alerting`'s currently-firing critical-severity alerts (a real,
   already-computed signal) plus one simple heuristic — a metric's current
   value compared against its own trailing-window average via
   `MetricsCollection` (basic percentage-deviation, not a trained model).
   Anything claiming true statistical anomaly detection (seasonality,
   trained baselines) is out of scope — same discipline as Decision #7.

9. **`POST /observability/export` serializes an already-computed result
   (dashboard, search, or correlation payload) to JSON or CSV — no new
   storage, no new computation.** Takes a `kind` + the same query params
   the corresponding `GET` endpoint takes, re-runs that composition, and
   returns it in the requested format instead of inventing a
   report-generation pipeline with its own persisted artifacts.

10. **`GET /observability/report` is a time-windowed, human-readable
    version of `/dashboard`** (e.g. "last 24h" rollup: total errors,
    incidents opened, anomaly count, fleet health snapshot at report time)
    — reuses Decision #4's composition, aggregated over a window instead of
    instantaneous. Not a scheduled/emailed report system — that's a
    genuinely separate piece of infrastructure (a scheduler + delivery
    mechanism) and explicitly out of scope for v1.

11. **This service holds no credentials of its own** — same non-duplication
    discipline as every prior service in this series. It only ever calls
    six sibling services' already-public REST APIs over one HTTP hop each;
    it never touches Loki/Tempo/Prometheus/Alertmanager/Pushgateway
    directly, and never opens a database/Redis/RabbitMQ connection of its
    own.

12. **Every touch to Tenent/APIGateway is additive, one line** — same
    `Route(...)` / enum member / config field pattern used for all six
    prior services in APIGateway's `RouteService`, `UpstreamService` enum,
    and `KONG_ROUTE_PREFIX_MAP`. Zero code changes to any of the six
    composed services themselves.

13. **Access control: operator-only**, same `require_operator_scope`
    pattern as every tier-3 service — investigation/correlation data spans
    the whole platform and has no tenant relevance, same reasoning as every
    prior service's equivalent decision.

## Explicitly Out of Scope for v1

- Real causal inference / automated root-cause diagnosis (Decision #7) —
  this service gathers correlated evidence, it does not compute a verdict
- Statistical/ML-based anomaly detection (Decision #8) — rule-based signals
  only
- A new incident-management datastore or lifecycle (create/acknowledge/
  resolve) — Decision #6, that's `Alerting`'s job, already built
- A new full-text/query-language search engine — Decision #5, this
  federates existing LogQL/TraceQL-backed search, it doesn't invent a third
  query language
- Scheduled/emailed reports — Decision #10, a report is computed on demand
  only
- Direct calls to any tier-1 backend (Loki/Tempo/Prometheus/Alertmanager/
  Pushgateway) — Decision #1
- mTLS / advanced gateway hardening — inherits whatever APIGateway/Kong
  decide for all upstreams

## Phase 0 — Precondition (tracked separately, not part of this build)

- [ ] `Logging`, `DistributedTracing`, `MetricsCollection`, `Monitoring`,
      `Alerting`, `HealthCheck` all rebuilt and running — this document's
      every later phase assumes their real, already-established APIs exist
      (cited throughout by the Decision each one documents in its own
      `TODO.md`)

## Phase 1 — Scaffold (no business logic)

- [x] Create `services/Observability/app/` mirroring the Enterprise Clean
      Architecture layout used by every prior service in this series:
      `api/v1/`, `core/`, `domain/`, `infrastructure/`, `repositories/`,
      `schemas/`, `services/`, `middleware/` (no `models/` — no database)
- [x] `pyproject.toml` + `uv.lock` — copy `services/HealthCheck/pyproject.toml`
      as a base (same dependency set)
- [x] `app/core/config.py` — `Settings`: base URLs for all six composed
      services (`LOGGING_BASE_URL`, `DISTRIBUTED_TRACING_BASE_URL`,
      `METRICS_COLLECTION_BASE_URL`, `MONITORING_BASE_URL`,
      `ALERTING_BASE_URL`, `HEALTH_CHECK_BASE_URL`); `SIBLING_TIMEOUT`;
      `SECRET_KEY`/`JWT_AUTH_ENABLED`/`JWT_ALGORITHM`; `CORS_ALLOW_ORIGINS`
- [x] `app/core/logging.py` — copy verbatim (best-effort `shared.observability`
      import, local fallback)
- [x] `app/main.py` — FastAPI app factory, lifespan startup: one shared
      `httpx.AsyncClient` for all sibling-service calls, OTel try/except
      pattern
- [x] `app/api/v1/health_router.py` — this service's own `/health`+`/ready`
      (no hard dependency to gate on — same reasoning as Monitoring's/
      Alerting's/HealthCheck's equivalents)
- [x] `Dockerfile` — copy the now-repeatedly-proven-clean
      `services/HealthCheck/Dockerfile` verbatim
- [x] `.env.example`, `.dockerignore`, `scripts/lint.sh`, `scripts/fix.sh`

## Phase 2 — Sibling clients (no business logic)

- [x] `app/infrastructure/siblings/logging_client.py` — thin wrapper over
      `Logging`'s `/api/v1/logs/search` (see `services/Logging/TODO.md` for
      its real query params)
- [x] `app/infrastructure/siblings/tracing_client.py` — thin wrapper over
      `DistributedTracing`'s `/api/v1/traces/search`
- [x] `app/infrastructure/siblings/metrics_client.py` — thin wrapper over
      `MetricsCollection`'s system-metrics + query endpoints
- [x] `app/infrastructure/siblings/monitoring_client.py` — thin wrapper over
      `Monitoring`'s `/monitoring/summary` (not the full dashboard — this
      service only needs the topology-level headline, per Decision #4)
- [x] `app/infrastructure/siblings/alerting_client.py` — thin wrapper over
      `Alerting`'s `/api/v1/alerts` (list) — same real endpoint Decision #6
      re-shapes, not a new one
- [x] `app/infrastructure/siblings/health_client.py` — thin wrapper over
      `HealthCheck`'s `/api/v1/health/dependencies` and `/health/live`
- [x] Every client degrades to `None`/empty on failure rather than raising
      — same "one dead sibling doesn't fail the whole response" rule every
      aggregator in this series follows

## Phase 3 — Domain model

- [x] `app/domain/observability.py` — dataclasses: `EvidenceItem` (source:
      "log"|"trace"|"metric"|"alert", timestamp, summary, raw payload),
      `TopologyEdge` (caller, callee, call_count), `TopologyNode` (service
      name, reachable, dependencies — from HealthCheck), `Incident`
      (alertname, first_seen, affected_services, severity),
      `AnomalySignal` (source, description, severity), `DashboardSummary`
      (the five composed headline numbers from Decision #4)
- [x] `app/domain/exceptions.py` — `NotAnOperatorError`

## Phase 4 — Topology (see Decisions #2/#3 — the one genuinely new data source)

- [x] `app/repositories/topology_repository.py` — parses
      `DistributedTracing`'s search results into `TopologyEdge`s by reading
      each trace's spans' `service.name` and parent/child relationships —
      real trace data, not invented
- [x] `app/services/topology_service.py` — `get_dependencies()` (Decision
      #2's graph alone), `get_topology()` (graph + `HealthCheck` health
      overlay, Decision #3)

## Phase 5 — Federated search + dashboard (see Decisions #4/#5)

- [x] `app/services/search_service.py` — concurrent fan-out to Logging +
      DistributedTracing, merged/time-ordered, tagged by source
- [x] `app/services/dashboard_service.py` — the five-way composition from
      Decision #4

## Phase 6 — Incidents + anomalies + evidence correlation (see Decisions #6/#7/#8)

- [x] `app/services/incident_service.py` — reshapes Alerting's `/alerts`
      into grouped `Incident`s
- [x] `app/services/anomaly_service.py` — the two real, rule-based signals
      from Decision #8
- [x] `app/services/correlation_service.py` — the evidence-gathering engine
      from Decision #7, used by both `/root-cause` and `/correlation`

## Phase 7 — Access control (operator-only — see Decision #13)

- [x] `app/middleware/auth.py` — copy verbatim
- [x] `app/api/v1/dependencies.py` — `require_operator_scope()`, copied
      from the established pattern

## Phase 8 — Core read + action API

- [x] `GET /api/v1/observability/dashboard` (Decision #4)
- [x] `GET /api/v1/observability/search?q=&from=&to=` (Decision #5)
- [x] `GET /api/v1/observability/root-cause?alert_id=` or `?trace_id=`
      (Decision #7)
- [x] `GET /api/v1/observability/incidents` (Decision #6)
- [x] `GET /api/v1/observability/dependencies` (Decision #2)
- [x] `GET /api/v1/observability/topology` (Decision #3)
- [x] `GET /api/v1/observability/anomalies` (Decision #8)
- [x] `GET /api/v1/observability/correlation?service=&from=&to=` (Decision #7)
- [x] `POST /api/v1/observability/export` (Decision #9)
- [x] `GET /api/v1/observability/report?window=24h` (Decision #10)
- [x] `app/schemas/observability.py` — response models for all of the above

## Phase 9 — Observability for the service itself

- [x] Dogfood `shared/observability`: `configure_logging()`, OTel tracing,
      `/metrics` via `prometheus_client`
- [x] Add this service's own scrape job to
      `services/MetricsCollection/prometheus/prometheus.yml` in the same
      pass as Phase 11's docker-compose entry — do not repeat the
      unscraped-`/metrics` gap that happened to Logging and
      DistributedTracing

## Phase 10 — Gateway integration (additive only — APIGateway changes)

- [x] `services/APIGateway/app/domain/enums.py` — add one
      `UpstreamService.OBSERVABILITY` member
- [x] `services/APIGateway/app/core/config.py` — add one
      `observability_base_url: str` setting
- [x] `services/APIGateway/app/services/route_service.py` — add one
      `Route(prefix="/api/v1/observability", upstream=UpstreamService.OBSERVABILITY,
      cacheable_methods=frozenset(), cache_ttl=0)` entry — never cacheable,
      investigation data is meaningless if stale
- [x] `services/APIGateway/app/services/kong_admin_service.py` —
      `KONG_ROUTE_PREFIX_MAP` gets one more entry
- [x] Update every APIGateway test that asserts an exact route count — by
      now a well-known, recurring checklist: `test_route_service.py`,
      `test_gateway_router.py` (routes total, prefix set,
      cacheable-methods/cache-ttl per-route, **and**
      `test_gateway_status_probes_unique_upstreams_only`'s unique-upstream
      count), `test_kong_admin_service.py`, `test_proxy_router.py`. Grep
      the whole `tests/` tree for the current literal route-count integer
      before declaring this phase done — the exact starting number depends
      on where the Phase 0 rebuild lands APIGateway's route count before
      this service's own addition.

## Phase 11 — Infra wiring

- [x] `docker-compose.yml` — new `observability` service block: `build:
      ./services/Observability`, next free host port, environment pointing
      at all six sibling services' in-network base URLs, same `backend`
      network, no `profiles:` restriction (cheap to run, degrades
      per-sibling)
- [x] `HEALTH_CHECK_BASE_URL`-style addition:
      `OBSERVABILITY_BASE_URL: http://observability:8000` on `api-gateway`'s
      environment block

## Phase 12 — Testing

- [x] Unit tests for `topology_repository.py`'s trace-to-graph parsing —
      the one piece of business logic in this entire service that's
      actually intricate, same "test the shape logic thoroughly" priority
      HealthCheck's `ready_shape_repository.py` got
- [x] Unit tests for each service-layer composer (`dashboard_service`,
      `search_service`, `incident_service`, `anomaly_service`,
      `correlation_service`) using fakes — assert one-dead-sibling
      degradation, same discipline every aggregator in this series is
      tested for
- [x] Unit tests for `require_operator_scope` — copy the established shape
- [ ] Before trusting this against real services: actually run it against
      the real docker-compose stack with all six siblings up, generate
      some real log/trace/metric/alert activity, and confirm `/dashboard`,
      `/search`, and `/topology` show real, correlated data rather than
      empty/degraded results — every prior service in this series found a
      real, non-obvious bug exactly at this step, so budget real time for
      it rather than trusting the composition logic from reading code alone
- [ ] `task test SERVICE=Observability` wired into root `Taskfile.yml`
      service list once `pyproject.toml` exists

## Implementation Notes (found while building)

1. **The one thing this implementation could not do that every prior
   service in this series did: verify composition logic against real
   sibling containers.** Logging, DistributedTracing, MetricsCollection,
   Monitoring, Alerting, and HealthCheck all exist on disk only as
   `README.md` again (Phase 0). What was verified instead: 55 unit tests
   (fakes for every sibling client, one test per real `/ready`-shape-style
   edge case in `topology_repository.py`/`incident_repository.py`,
   one-dead-sibling-degrades-only-itself for every composer), a clean
   `ruff`/`mypy` pass, and a real Docker build + container run with all six
   sibling URLs pointed at nonexistent hosts — confirmed the service starts
   cleanly and every endpoint degrades to honest `null`/empty results
   rather than crashing. That last check is real evidence the DI wiring
   and error handling work end-to-end; it is not evidence the sibling
   clients' assumed JSON shapes (Logging, DistributedTracing,
   MetricsCollection, Monitoring) are correct — those need re-verification
   against real containers once Phase 0 is done, per this phase's last
   unchecked item.
2. Alerting's and HealthCheck's client shapes (`alerting_client.py`,
   `health_client.py`) are the two exceptions — both were built and
   verified against real Alertmanager/Prometheus containers earlier in
   this project's history and were fresh enough in context to transcribe
   precisely (field names, nesting, the exact `/health/live` vs
   `/health/dependencies` distinction) rather than reconstruct from the
   TODO.md summaries alone. Treat these two as higher-confidence than the
   other four sibling clients until Phase 0's rebuild allows re-verifying
   all six for real.
3. `topology_repository.py`'s trace-to-graph mining (TODO.md Decision #2)
   was the one piece of genuinely new logic in this service — not a
   composition of an existing endpoint's output, but a real mining
   algorithm over assumed span data. Given DistributedTracing doesn't
   exist to verify the assumed `spans`/`span_id`/`parent_span_id`/
   `service_name` shape against, this is the single highest-risk
   assumption in the whole service and the first thing to check once
   Phase 0 lands — see `tracing_client.py`'s docstring for the exact
   caveat.
