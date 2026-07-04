# ObservilityManagement — 3-Phase Implementation Plan

**Status: Fully implemented — all three phases done, verified against
real containers, and the seven original services decommissioned.** All
seven directories (`Monitoring`, `Logging`, `DistributedTracing`,
`MetricsCollection`, `Alerting`, `Observability`, `HealthCheck`) are now
gone from `services/` entirely, including the tier-1 backend config
subdirectories the "Current state, read first" section below originally
called out as preserved — see Phase 3.4 and Implementation Note #5 for how
that went further than this plan originally called for, one service at a
time, by explicit user request. See Implementation Notes at the bottom for
what real-container verification found and exactly what "decommissioned"
ended up meaning in practice.

**What this is:** merging seven separate microservices — `Monitoring`,
`Logging`, `DistributedTracing`, `MetricsCollection`, `Alerting`,
`Observability`, `HealthCheck` — into one deployable FastAPI service,
`ObservilityManagement`.

**Current state, read first:** of the seven, only `services/Observability/`
currently has real code on disk (39 `.py` files, 55 passing tests, its own
`TODO.md`) — it was built most recently, after the others were lost to an
out-of-band branch switch that discarded uncommitted work. The other six
exist only as their original `README.md` (plus a few static config
directories — `Alerting/alertmanager/`, `Alerting/prometheus/`,
`Logging/loki/`, `Logging/promtail/`, `DistributedTracing/tempo/`,
`MetricsCollection/prometheus/`, `MetricsCollection/otelcol/`,
`Monitoring/grafana/` — these are tier-1 backend configs, not application
code, and are unaffected by this merge either way). Their own `TODO.md`
design docs were lost along with their code, so **this document also
carries forward every decision from those six lost `TODO.md`s that still
matters** — see "Consolidated Design Decisions" below — since this plan is
the only place that knowledge survives now.

Because six of the seven have no code to "merge" in the literal sense,
Phase 1/2 below are really "build these six domains, directly as internal
modules of the new service, using their previously-established designs" —
not "merge seven working services." There is no value in rebuilding them
standalone first only to merge them a moment later.

## Consolidated Design Decisions

1. **One process, one container, one port — but the same seven URL
   prefixes, preserved exactly.** `ObservilityManagement` mounts seven
   routers in one FastAPI app: `/api/v1/logs`, `/api/v1/traces`,
   `/api/v1/metrics`, `/api/v1/monitoring`, `/api/v1/alerts`,
   `/api/v1/observability`, `/api/v1/health` — the exact prefixes each
   original service used. This is a "modular monolith" for the
   observability domain, not a redesign of the API surface: anything that
   already knows these paths (APIGateway's route registry, Kong, any
   external client) keeps working, only the number of backend containers
   it's proxying to drops from seven to one.

2. **Domain module layout, one subpackage per merged service:**
   `app/domains/{logging,tracing,metrics,monitoring,alerting,health,observability}/`,
   each with its own `repositories/`, `services/`, `schemas/`, `router.py`
   — mirroring the Enterprise Clean Architecture layout every one of the
   seven originals already used, just nested one level deeper instead of
   spread across seven repos. Shared code (`core/config.py`,
   `core/logging.py`, `middleware/`, the `require_operator_scope` pattern)
   lives once at `app/core` / `app/middleware`, not duplicated seven times.

3. **One shared httpx client pool for the five *raw* tier-1 backends**
   (Loki, Tempo, Prometheus, Pushgateway, Alertmanager) — built once in
   `app/main.py`'s lifespan and injected via FastAPI `Depends`, the same
   way every original service built exactly one `httpx.AsyncClient` for
   its own backend. No change to *how* each domain talks to its backend,
   only *where* the client instance is constructed.

4. **In-process composition replaces HTTP composition for
   `Observability`'s domain — this is the one real architectural change,
   not just a relocation.** Today, `Observability`'s five composition
   services (`dashboard_service`, `search_service`, `topology_service`,
   `incident_service`, `anomaly_service`, `correlation_service`) call
   `app/infrastructure/siblings/*_client.py` wrappers that make an HTTP
   request to another container. Once merged, those six wrapper classes
   are deleted and replaced with direct calls to the other domains' own
   service classes (`app.domains.logging.services.LogQueryService`,
   `app.domains.tracing.services.TraceQueryService`, etc.) — a plain
   Python function call, not a network hop. Graceful degradation is
   **preserved, one layer down**: each domain's own repository/service
   already catches its *own* backend being unreachable (Loki down, Tempo
   down, ...) and returns `None`/empty, exactly as it does today; wrap
   every cross-domain call `Observability` makes in a `try/except
   Exception` regardless, so a genuine bug in one domain (not just its
   backend being down) can't take down the whole aggregation — a slightly
   stronger guarantee than the HTTP version had, since an HTTP call
   couldn't accidentally propagate an unrelated Python exception across
   the wire the way an in-process call could.

5. **`HealthCheck`'s job shrinks — and that shrinkage should be embraced,
   not worked around.** Its entire reason for existing was normalizing the
   fleet's mismatched `/ready` shapes (a real list-shape, dict-shape,
   flat-string-shape, flat-boolean-shape, and no-shape-at-all across seven
   services — see its own lost `TODO.md` Decision #1, reproduced in Phase
   2 below). Once Logging/DistributedTracing/MetricsCollection/Monitoring/
   Alerting/Observability are one process, there is only **one** `/ready`
   for all of them combined (this service's own), plus whatever Tenent and
   APIGateway still report — down from normalizing seven shapes to
   normalizing three. `HealthCheck`'s domain module keeps this narrower,
   genuinely useful scope (Tenent + APIGateway + itself) rather than being
   quietly kept alive at its old scope out of inertia.

6. **APIGateway simplification is a real, additive-only side effect, not
   scope creep.** `UpstreamService`'s six members —
   `LOGGING`/`DISTRIBUTED_TRACING`/`METRICS_COLLECTION`/`MONITORING`/
   `ALERTING`/`HEALTH_CHECK` (plus the already-separate `OBSERVABILITY`) —
   collapse into **one** `OBSERVABILITY_MANAGEMENT` member and **one**
   `observability_management_base_url` setting. `RouteService`'s registry
   keeps all seven `Route(...)` entries (Decision #1), just pointed at the
   same base URL instead of seven different ones — `gateway_status`'s
   existing dedup-by-upstream logic then correctly probes this backend's
   `/health` exactly once instead of seven times, which is a correctness
   improvement, not a loss of information (all seven were always the same
   liveness question — "is this container up" — asked seven redundant
   times).

7. **Every hard-won, backend-specific decision from the six lost
   `TODO.md`s carries forward unchanged** — restated per-domain in Phase 1
   /2 below so this is the one place they're preserved. None of these are
   being reconsidered by the merge; the merge changes *how many containers
   run this code*, not *what the code does*.

8. **Migration order follows the dependency graph, not the numbered list
   in the request.** Tier-1 query domains (Logging, DistributedTracing,
   MetricsCollection) depend on nothing but their own raw backend, so they
   can be built first with zero risk of churn from a domain that depends
   on them changing underneath them. Tier-3 composers (Monitoring,
   Alerting, HealthCheck) depend on tier-1 domains plus external services
   (Tenent, APIGateway) but not on tier-4. Tier-4 (`Observability`) depends
   on everything and goes last. This is why Phase 1 and Phase 2 don't
   match the request's "71/72/.../77" ordering literally.

## Explicitly Out of Scope for This Merge

- Redesigning any domain's API surface, request/response schema, or query
  language (LogQL/TraceQL/PromQL) — this is a deployment consolidation,
  not a rewrite
- A unified data model across logs/traces/metrics/alerts — each domain
  keeps its own schemas; only the *process* they run in is shared
- Removing any of the seven URL prefixes — Decision #1
- Touching Tenent or the tier-1 raw backends (Loki/Tempo/Prometheus/
  Alertmanager/Pushgateway/Grafana/OTel Collector) — out of scope, unaffected
- Deleting the seven original `services/*/` directories before
  `ObservilityManagement` is built, tested, and Docker-verified — Phase 3's
  explicit last step, never earlier

---

## Phase 1 — Scaffold + Tier-1 Query Domains (Logging, Tracing, Metrics)

### 1.0 Scaffold
- [x] `services/ObservilityManagement/app/` with `core/`, `middleware/`,
      `domains/`, `main.py` — copy the established `core/config.py`
      pattern (superset `Settings` with every env var all seven services
      used: `LOKI_BASE_URL`, `TEMPO_BASE_URL`, `PROMETHEUS_BASE_URL`,
      `PUSHGATEWAY_BASE_URL`, `ALERTMANAGER_BASE_URL`,
      `TENENT_BASE_URL`, `API_GATEWAY_BASE_URL`,
      `MANAGED_RULES_FILE_PATH`/`MANAGED_RULES_GROUP_NAME` (Alerting),
      `DEFAULT_ACKNOWLEDGE_MINUTES` (Alerting),
      `DEFAULT_WINDOW_MINUTES` (Observability), JWT/CORS/OTel settings)
- [x] `pyproject.toml` — union of all seven `pyproject.toml`s' dependencies
      (adds `pyyaml` for Alerting's rule-file store on top of
      Observability's existing dependency set)
- [x] `app/main.py` — one lifespan building the five raw-backend
      `httpx.AsyncClient`s (Decision #3), one `/health`+`/ready` for the
      whole process, one `/metrics` mount
- [x] `Dockerfile`, `.env.example`, `.dockerignore`, `scripts/lint.sh`,
      `scripts/fix.sh` — copy the now-seven-times-proven-clean pattern

### 1.1 Logging domain (`app/domains/logging/`)
- [x] Query layer over Loki — LogQL search, verbatim from the lost
      `services/Logging/TODO.md`'s design: never expose raw LogQL to
      callers, build queries server-side; router at `/api/v1/logs`
- [x] `LogQueryService` — the plain service class `Observability`'s
      domain will import directly in Phase 2 (Decision #4)

### 1.2 DistributedTracing domain (`app/domains/tracing/`)
- [x] Query layer over Tempo — TraceQL search, same server-side-only
      query-construction rule as Logging; router at `/api/v1/traces`
- [x] `TraceQueryService` — including whatever span shape
      (`span_id`/`parent_span_id`/`service_name`) real Tempo search
      results actually have, verified this time against a **real Tempo
      container** before `topology_repository.py` (ported in Phase 2)
      trusts it — this was the single highest-risk unverified assumption
      flagged in `services/Observability/TODO.md`'s Implementation Notes,
      and this phase is the first opportunity to close it for real

### 1.3 MetricsCollection domain (`app/domains/metrics/`)
- [x] Query layer over Prometheus + push layer over Pushgateway — carries
      forward the lost `TODO.md`'s Decision #1 (dead `nutratenant_http_*`
      metric names — verify whether that gap has since been closed by
      Tenent/APIGateway actually wiring `shared/observability/metrics`; if
      not, same documented gap applies) and its node-exporter-absence
      decision for system metrics
- [x] `MetricsQueryService` — used directly by `Monitoring` (Phase 2) and
      `Observability` (Phase 2) instead of an HTTP client

### 1.4 Testing
- [x] Unit tests per domain (query-building logic, response parsing) —
      same bar as the original three services individually met
- [x] Confirm all three domains' routers mount cleanly in one `FastAPI()`
      app with no path collisions

---

## Phase 2 — Tier-3 Composers + Tier-4 Observability (in-process)

### 2.1 Monitoring domain (`app/domains/monitoring/`)
- [x] Cross-service reachability/topology — carries forward the lost
      `TODO.md`'s core decision: reuse APIGateway's
      `GET /api/v1/gateway/status` fan-out rather than re-probing every
      upstream, compose Tenent's `/ready` for resource health, no
      tenant-scoped view (no `tenant_id` on any metric/span). Router at
      `/api/v1/monitoring`
- [x] Note: with Logging/Tracing/Metrics/Alerting now co-located,
      `gateway_status`'s upstream list (post Decision #6) reflects that —
      `Monitoring`'s own composition logic doesn't need to change, it's
      already written to tolerate however many upstreams `gateway_status`
      reports

### 2.2 Alerting domain (`app/domains/alerting/`)
- [x] Alert query/action layer over Alertmanager (list, push,
      acknowledge-via-silence, best-effort resolve, synthetic test-alert)
      — carries forward the lost `TODO.md`'s real, verified mechanics:
      acknowledge = create a real Alertmanager silence; resolve is
      real for externally-pushed alerts, best-effort for Prometheus-sourced
      ones
- [x] Dynamic alert-rule CRUD — carries forward the exact, real
      infra mechanics already verified against live containers before:
      a YAML file this domain exclusively writes
      (`MANAGED_RULES_FILE_PATH`), Prometheus started with
      `--web.enable-lifecycle`, `POST /-/reload` after every write, static
      rules protected from mutation (409 if attempted)
- [x] Re-apply the two real bugs already found and fixed once in the
      now-lost `prometheus/alerts/*.yml` files, since those files'
      `git ls-files` status showed they *are* still tracked/present on
      disk (`services/Alerting/alertmanager/`,
      `services/Alerting/prometheus/` survived — only the `app/` code was
      lost) — **check whether `humanizeBytes` (invalid Prometheus template
      function, made Prometheus refuse to start entirely) and
      `TenantActivePoliciesLow` (permanent false-positive from an unlabeled
      Gauge Tenent never sets) are still present in those surviving YAML
      files before assuming they need re-fixing** — they may already be
      fixed if those specific files weren't touched by whatever reverted
      the `app/` directories
- [x] Router at `/api/v1/alerts`

### 2.3 HealthCheck domain (`app/domains/health/`)
- [x] Fleet health normalization — carries forward the lost `TODO.md`'s
      real shape-dispatch design (list-shape, dict-shape,
      flat-string-shape, flat-boolean-shape, no-shape), but **the target
      registry shrinks to Tenent + APIGateway + this service's own
      `/ready`** (Decision #5) — down from eight targets to three
- [x] `/health/dependencies`, `/health/version`, `/health/live`,
      `/health/ready`, `/health/startup` (alias of ready),
      `/health/database`, `/health/cache`, `/health/message-broker`,
      `/health/details` — same nine endpoints, smaller registry
- [x] Router at `/api/v1/health`

### 2.4 Observability domain (`app/domains/observability/`) — port existing code, rewire composition
- [x] Copy `services/Observability/app/domain/`, `schemas/`,
      `api/v1/observability_router.py`, and the five service-layer
      composers verbatim as a starting point (this domain has real,
      tested code today, unlike the other five in this phase)
- [x] Delete `app/infrastructure/siblings/*_client.py` (six httpx-based
      wrapper classes) — replace every call site in
      `dashboard_service.py`, `search_service.py`, `topology_service.py`,
      `incident_service.py`, `anomaly_service.py`, `correlation_service.py`
      with a direct import of the corresponding in-process service class
      from `app.domains.{logging,tracing,metrics,monitoring,alerting,health}`
      (Decision #4)
- [x] Wrap every cross-domain call in `try/except Exception` per Decision
      #4's stronger-guarantee reasoning — re-run all 55 existing tests
      (now using in-process fakes instead of httpx-mocked ones) and
      confirm the same one-dead-source-degrades-only-itself behavior
      still holds
- [x] `topology_repository.py`'s trace-to-graph mining — re-verify its
      assumed span shape against Phase 1.2's real Tempo-backed
      `TraceQueryService` output now that it's available, closing the
      exact gap flagged in `services/Observability/TODO.md`'s
      Implementation Notes
- [x] Router at `/api/v1/observability` (unchanged)

### 2.5 Testing
- [x] Every domain's existing test suite ported and passing inside the
      merged app
- [x] New integration tests proving in-process composition actually works
      — e.g. push a real alert through the Alerting domain, confirm the
      Observability domain's `/incidents`/`/anomalies` see it without any
      network hop, in the same test process

---

## Phase 3 — Infra Cutover + Decommission

### 3.1 Single container
- [x] One `docker-compose.yml` service block, `observability-management`,
      port **8020** (first unused port after every port this project has
      allocated so far), replacing the *would-have-been* six/seven
      separate blocks — since only `Observability`'s block currently
      exists in `docker-compose.yml`, this is mostly a fresh addition, not
      a removal of six existing blocks
- [x] One Prometheus scrape job (`observability-management`) replacing
      the seven that would otherwise exist — again, currently only one
      (`observability`) exists in `services/MetricsCollection/prometheus/prometheus.yml`,
      so this is mostly addition, with that one job renamed/repointed
- [x] The dynamic-alert-rules volume mount (Alerting's Decision #4 — a
      sibling, not nested, host path shared read-write with this
      container and read-only with Prometheus) carries forward unchanged

### 3.2 APIGateway cutover (additive, then subtractive in one pass — see Decision #6)
- [x] Add `UpstreamService.OBSERVABILITY_MANAGEMENT` and
      `observability_management_base_url`
- [x] Point all seven existing/planned `Route(...)` entries
      (`/api/v1/logs`, `/api/v1/traces`, `/api/v1/metrics`,
      `/api/v1/monitoring`, `/api/v1/alerts`, `/api/v1/observability`,
      `/api/v1/health` — only `/api/v1/observability` currently exists in
      `route_service.py` today, per this project's current state) at the
      single new base URL
- [x] Remove the now-redundant `UpstreamService.OBSERVABILITY` member and
      `observability_base_url` setting (folded into
      `OBSERVABILITY_MANAGEMENT`) — update every test that names it
      specifically
- [x] Update every route-count-asserting test — the familiar checklist:
      `test_route_service.py`, `test_gateway_router.py` (including
      `test_gateway_status_probes_unique_upstreams_only`),
      `test_kong_admin_service.py`, `test_proxy_router.py`

### 3.3 Verification before decommission (do not skip)
- [x] Full test suite green inside `ObservilityManagement`
- [x] Real Docker build + container run, same discipline as every prior
      service in this project — at minimum, confirm `/api/v1/logs/search`,
      `/api/v1/traces/search`, `/api/v1/metrics/system`,
      `/api/v1/monitoring/status`, `/api/v1/alerts`,
      `/api/v1/observability/dashboard`, and `/api/v1/health/dependencies`
      all respond correctly from the one container against real
      Loki/Tempo/Prometheus/Alertmanager/Pushgateway backends
- [x] APIGateway's full test suite green with the cutover applied

### 3.4 Decommission (destructive — confirmed with the user before running)
- [x] **Correction to this phase's original plan, found before executing
      it**: "delete the seven directories in their entirety" turned out to
      be wrong. `docker-compose.yml` mounts 12 config files out of five of
      these directories' subdirectories directly into the tier-1 backend
      containers this same merged service talks to —
      `Alerting/alertmanager/`, `Alerting/prometheus/` (both the static
      `alerts/` and the writable `dynamic-alerts/`), `Logging/loki/`,
      `Logging/promtail/`, `DistributedTracing/tempo/`,
      `MetricsCollection/prometheus/`, `MetricsCollection/otelcol/`,
      `Monitoring/grafana/`. Deleting those would have broken
      Loki/Tempo/Prometheus/Alertmanager/Grafana/Promtail on the next
      `docker compose up`. Confirmed with the user before proceeding (see
      Implementation Notes) rather than either silently doing the
      originally-planned full deletion or silently doing a different,
      unapproved partial one.
- [x] `Observability/` and `HealthCheck/` had no config subdirectories to
      preserve and were deleted in full from the start.
- [x] **All five remaining services — `Monitoring/`, `Logging/`,
      `DistributedTracing/`, `MetricsCollection/`, and finally
      `Alerting/` — ended up deleted in full, by explicit, incremental,
      per-service user request**, superseding this phase's original
      "keep each config subdirectory in place" plan. Each was verified
      domain-by-domain before removal (real implementation re-read against
      the design decisions below, that domain's tests run in isolation,
      then the full suite) rather than assuming the earlier bulk pass or
      an earlier service's verification covered it adequately:
    - **Monitoring**: 19/19 domain tests, 95/95 full suite.
      `Monitoring/grafana/` relocated to
      `services/ObservilityManagement/grafana/` (`git mv`, preserving
      history) before deleting `services/Monitoring/`; both
      `docker-compose.yml` volume-mount sources for the `grafana` service
      repointed at the new path.
    - **Logging**: 13/13 domain tests, 95/95 full suite.
      `Logging/loki/` and `Logging/promtail/` relocated to
      `services/ObservilityManagement/loki/` and `.../promtail/` (`git mv`)
      before deleting `services/Logging/`; both `docker-compose.yml`
      volume-mount sources for the `loki` and `promtail` services
      repointed at the new paths.
    - **DistributedTracing**: 20/20 domain tests (including the topology-
      mining tests that depend on real Tempo span shape), 95/95 full suite.
      `DistributedTracing/tempo/` relocated to
      `services/ObservilityManagement/tempo/` (`git mv`, carrying forward
      the already-fixed `metrics_generator.processors` bug from
      Implementation Note #1) before deleting `DistributedTracing/`; the
      `tempo` service's `docker-compose.yml` volume-mount source repointed
      at the new path.
    - **MetricsCollection**: 9/9 domain tests, 95/95 full suite.
      `MetricsCollection/prometheus/` (main config + `rules/`) and
      `MetricsCollection/otelcol/` relocated to
      `services/ObservilityManagement/prometheus/` and `.../otelcol/`
      (`git mv`, carrying forward the already-renamed `observability` →
      `observability-management` scrape job and the removed stale scrape
      target from Implementation Note #2) before deleting
      `MetricsCollection/`; the `prometheus` service's two
      `docker-compose.yml` mount sources (main config, `rules/`) and the
      `otel-collector` service's one mount source repointed at the new
      paths. Note: Prometheus's config surface is still split across two
      directories after this move — `ObservilityManagement/prometheus/`
      (main config + recording rules, from here) and `Alerting/prometheus/`
      (alert rules + the dynamic-alerts write target, untouched by this
      step) — both are legitimate, separately-owned mount sources for the
      same container, not a leftover inconsistency; they'd only both land
      under one path if `Alerting/` is later removed the same way.
    - **Alerting**: 23/23 domain tests (alert query/action + rule-file
      CRUD) plus the in-process-composition test proving one pushed alert
      is visible through Alerting, Monitoring, and Observability with
      zero network hops, 95/95 full suite. `Alerting/alertmanager/`
      relocated to `services/ObservilityManagement/alertmanager/`;
      `Alerting/prometheus/alerts/` and `Alerting/prometheus/dynamic-alerts/`
      relocated into the `services/ObservilityManagement/prometheus/`
      directory already created by the MetricsCollection move — resolving
      that move's noted wrinkle, Prometheus's config now comes from exactly
      one directory (main config, recording rules, static alert rules, and
      the dynamic-alerts read-write target all under
      `ObservilityManagement/prometheus/`) instead of two. Four
      `docker-compose.yml` mount sources repointed: the
      `observability-management` service's own read-write mount of
      `dynamic-alerts` (`/data/rules`, `MANAGED_RULES_FILE_PATH`'s target),
      `prometheus`'s two mounts (`alerts/`, and its own read-only view of
      the same `dynamic-alerts/`), and `alertmanager`'s config mount.
    - All five moves verified with `docker compose config --quiet` (clean,
      aside from pre-existing `.env`-file-not-found warnings for unrelated
      services this work never touched) and confirmed the source directory
      no longer exists on disk. The merged service is now the config home
      for every tier-1 backend this project runs, the same way it's
      already the home for every domain's application code — with
      `Alerting/` gone, `services/` no longer contains any of the seven
      original service directories at all; this was a deliberate,
      per-request, one-at-a-time departure from the original
      config-preservation default, verified independently at each step
      rather than done as one bulk pass.
- [x] Verified every `docker-compose.yml` volume-mount source path still
      resolves on disk after the cleanup, and re-ran both this service's
      and APIGateway's full test suites to confirm nothing broke.

## Implementation Notes (found while building)

1. **A second real, previously-undiscovered config bug** — this time in
   `services/DistributedTracing/tempo/tempo.yml`, which survived the
   earlier code-loss incident since it's a config file, not application
   code. `metrics_generator.processors` was set as a direct child of
   `metrics_generator` — invalid for this Tempo version
   ("field processors not found in type generator.Config"), and **fatal**:
   Tempo refused to start at all. The file already had the *correct* way
   to configure this two lines below, under `overrides.defaults.metrics_generator.processors`
   — the invalid duplicate was simply deleted. Found by actually booting a
   real `grafana/tempo:2.5.0` container against this file during Phase
   3.3's verification, the same "run it for real" discipline that has now
   caught a fatal, repo-wide-silent config bug in every backend this
   project touches (Prometheus's `humanizeBytes` in Alerting's build,
   Tempo's `processors` placement here).
2. **A stale Prometheus scrape job** (`job_name: observability`, pointing
   at a hostname that no longer resolves to anything once the merge
   replaced it with `observability-management`) was found and removed
   from `services/MetricsCollection/prometheus/prometheus.yml` while
   validating the merged scrape config — a real instance of exactly the
   "safety check, not expected to find much" scenario Phase 3.4's original
   wording anticipated, except it did find something.
3. **The decommission step's original plan (Phase 3.4) was wrong in a way
   that mattered before any deletion happened**: it assumed all seven
   directories could be deleted wholesale once the replacement was
   verified. Actually inspecting what `docker-compose.yml` mounts from
   inside those directories (12 active volume-mount sources feeding
   Loki/Tempo/Prometheus/Alertmanager/Grafana/Promtail/OTel-Collector)
   showed that five of the seven still hold load-bearing infrastructure
   config, not just orphaned application code. Caught this before running
   any destructive command, surfaced it to the user with the specific
   `grep` evidence, and got an explicit decision on how to proceed rather
   than guessing — the corrected plan (delete only `README.md`/`TODO.md`/
   `app/`/`tests/`/tool-caches, keep each service's config subdirectory)
   is what Phase 3.4 above actually reflects now.
4. In-process composition (Decision #4) was verified twice: once via unit
   tests with fakes (`test_monitoring_service.py`'s
   `test_get_status_degrades_alert_count_when_alerting_raises`,
   `test_in_process_composition.py`), and once for real — pushed a
   synthetic alert through the real Alerting domain against a real
   Alertmanager container, then confirmed the *same* alert was
   consistently visible through `/monitoring/status`'s `active_alert_count`,
   `/observability/incidents`, `/observability/anomalies`, and
   `/observability/dashboard`'s `active_alert_count` — all four reached
   through completely different code paths into the same one
   `AlertService.list_alerts()` call, zero network hops between domains,
   with matching counts every time.
5. **Independent re-audit of the decommission, done cold in a separate
   session against the working tree as it stood (not by re-trusting this
   file's own checkmarks):** full fresh test runs
   (`ObservilityManagement`: 95/95 passed; `APIGateway`: 107/107 passed
   with the cutover applied), a repo-wide grep for every old hostname/
   enum/import path (`observability:`/`logging:`/`distributed-tracing`/
   `metrics-collection:`/`monitoring:`/`alerting:`/`healthcheck:` as
   compose hostnames, `UpstreamService.OBSERVABILITY` as a bare enum
   reference, `services/Observability` path references) — zero hits
   anywhere (compose, Kong, Grafana provisioning, CI workflows, root
   README's service catalog is prose-only and unaffected), and a
   `docker-compose.yml` service-block enumeration confirming exactly one
   app container (`observability-management`) plus the unchanged tier-1
   backends (`prometheus`, `tempo`, `loki`, `promtail`, `grafana`,
   `alertmanager`, `otel-collector`) — no leftover per-service app blocks,
   no dangling `depends_on`. `ci.yml`'s service discovery
   (`find . -maxdepth 2 -name pyproject.toml`) and `cd.yml`'s matrix
   needed no edits either way: the former naturally stopped seeing the
   five config-only directories once their `pyproject.toml`s were deleted,
   and the latter never listed these services by name. One pre-existing,
   unrelated condition was checked and ruled a non-issue rather than a
   regression: `ObservilityManagement`'s 5 mypy `import-not-found` errors
   on `shared.observability.*` are the same error `Tenent` and
   `APIGateway` already have today (both wrap the same imports in
   `try/except` inside `main.py`) — a project-wide, pre-existing gap in
   how `shared/` is exposed to each service's mypy run, not something this
   merge introduced or regressed.
