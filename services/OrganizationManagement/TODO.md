# OrganizationManagement — Implementation Notes

**Status: Implemented.** Every endpoint in `README.md`'s API Reference is
live; 19/19 tests pass; wired into `docker-compose.yml` and APIGateway's
route registry; Docker image builds and boots for real (see "Docker
build/run" below — a build-breaking Dockerfile bug was found and fixed
here).

## What this is

Per `Implementation-order.md`, Organization is the next service after Tenant
Management (`services/Tenent/`) in the platform's build order — the
top-level business entity a tenant owns, and the root container for
workspaces/teams/groups/members/resources described in `README.md`.

## Design Decisions

1. **Directory renamed from `Organization Management` (with a space) to
   `OrganizationManagement`.** Every other real, implemented service in
   this repo (`IAM`, `Tenent`, `APIGateway`, `ObservilityManagement`) uses
   PascalCase with no space; the space appears to have been a bootstrap
   artifact on this one placeholder directory (and on the still-unbuilt
   `Workspace Management`, left untouched — out of scope for this work).
   A space in a path used by Docker build contexts, Taskfile commands, and
   shell scripts is fragile; renamed before writing any code against it.

2. **Layout mirrors `services/Tenent/`, not `services/ObservilityManagement/`.**
   Tenent's flat layered structure (`models/`, `repositories/`, `services/`,
   `schemas/`, `api/v1/`) fits a single-domain CRUD service; ObservilityManagement's
   `domains/{name}/` subpackage-per-merged-service layout exists specifically
   because it merged seven previously-separate services — Organization isn't
   a merge, so that extra nesting would be unearned complexity.

3. **Every request is scoped by the `X-Tenant-ID` header**, not a URL path
   segment — matching `README.md`'s own API Reference note ("All requests
   must include appropriate multi-tenant routing identifiers (e.g.,
   `X-Tenant-ID` header)"). Every repository query and the `get_organization_or_404`
   dependency filter by `(organization_id, tenant_id)` together, so an
   organization created under tenant A is a 404 — not a 403, to avoid leaking
   existence — to a caller presenting tenant B's header, even with the
   correct UUID. Covered by `test_get_organization_wrong_tenant_is_not_found`.

4. **`tenant_id` is a projection field, not a foreign key** — same rule
   this project's IAM service documents for its `UserProjection` model and
   Tenent documents for `owner_id`. `TenentClient.assert_tenant_exists()`
   makes one synchronous HTTP call to Tenent's `GET /api/v1/tenants/{id}`
   at organization-creation time only (not stored, not polled again) and
   raises a domain exception the router turns into 404/503 — deliberately
   *not* the fire-and-log pattern Tenent itself uses when notifying
   TenantProvisioning (that's a side effect allowed to be best-effort;
   creating an organization under a nonexistent tenant_id is a real
   correctness error the caller needs to see).

5. **`OrganizationSettings.feature_flags`/`compliance_rules` use
   `sqlalchemy.JSON`, not `postgresql.JSONB`.** This project's IAM service
   already hit the JSONB/SQLite trap once (documented in its
   `models/__init__.py`: Policy/Resource models using JSONB "must NOT be
   added to `app/models/__init__.py` because it causes test failures with
   SQLite"). The dialect-generic `JSON` type avoids that failure mode by
   construction rather than by a workaround — it compiles to a real JSON
   column on Postgres and a TEXT-backed one on SQLite, both usable
   identically from the ORM layer, so this service's tests run against
   real SQLite without special-casing these two columns.

6. **`OrganizationStatus` has two states, not Tenant's seven.** `README.md`'s
   documented API surface is create/list/get/patch/delete plus settings/
   stats/sub-resource-enumeration — no provisioning workflow, no
   suspend/archive transition is asked for anywhere in it. Modeling a
   `TenantStatus`-style 7-state machine here would be speculative: extra
   states and transitions this service has no caller for yet. `active` →
   `deleted` (terminal, via soft-delete) is the whole enum;
   `VALID_TRANSITIONS` follows the same dict-of-frozensets shape as
   Tenent's so extending it later is a small diff, not a redesign.

7. **Workspaces/Teams/Groups/Members sub-resource enumeration endpoints
   are real (implemented, tested, return 200) but honestly empty.**
   `Implementation-order.md` lists Organization *before* User Management,
   Group, and Membership — none of those owning services exist yet in this
   repo. `OrganizationService.list_members/list_workspaces/list_teams/list_groups`
   return `{"items": [], "total": 0}` rather than inventing local storage
   for a domain this service doesn't own — the same restraint this
   project already applies elsewhere to a documented, not-yet-closed gap
   (`ObservilityManagement`'s `MetricsQueryService.system_metrics()` querying
   only `up` because no node-exporter is deployed, rather than fabricating
   host metrics). `get_stats()` follows the same rule: real `organization_id`/
   `status`/`created_at`, honest `0` counts for the four sub-resources.

8. **Dependency-injected `OrganizationService` via FastAPI `Depends`, not a
   per-request `_svc(db)` helper closure.** Tenent's routers use a bare
   `def _svc(db) -> TenantService: return TenantService(db)` helper, which
   works but means test overrides have to go through the DB session
   fixture indirectly. This service instead defines
   `get_organization_service()` (itself composed from `get_db` +
   `get_tenent_client`) as a proper FastAPI dependency
   (`app/api/v1/dependencies.py`), the same pattern
   `ObservilityManagement`'s alerting-domain tests already rely on
   (`app.dependency_overrides[get_rule_service]`). This is what lets
   `tests/unit/test_organizations.py` override just the Tenent-validation
   behavior per-test (`test_create_organization_tenant_not_found`,
   `test_create_organization_tenant_service_unavailable`) without touching
   the database session override at all — cleaner separation of concerns,
   consistent with the dependency-inversion half of the SOLID principles
   this build was asked to follow.

9. **No Redis, no RabbitMQ, no rate limiting.** Tenent's merged config
   carries all three because TenantIsolation needed Redis for cache and
   TenantProvisioning-notification needed messaging. Nothing in
   `README.md`'s API surface asks for caching, pub/sub, or rate limiting,
   and per this project's own repeated pattern (`ObservilityManagement`
   dropped Tenent's Redis/RabbitMQ/slowapi stack too, for the same
   reason) — not adding infrastructure a service doesn't use.

10. **Not cacheable at the gateway.** APIGateway's `route_service.py`
    registers `/api/v1/organizations` with `cacheable_methods=frozenset()`,
    `cache_ttl=0` — the same treatment `ObservilityManagement`'s seven
    prefixes get, for the same reason: no domain-event publisher wires
    organization writes into a cache-invalidation signal yet, so caching
    GETs here would risk serving stale data after an update/delete with
    nothing to bust it. Revisit once (if) this service publishes
    `organization.updated`/`organization.deleted` events Tenent-style.

## Wiring

- `docker-compose.yml`: new `organization-management` service, port
  **8021** (next unused after ObservilityManagement's 8020), Postgres-only
  `depends_on` (no Redis/RabbitMQ needed — Decision #9).
  `infrastructure/postgres/init.sql` now also creates the
  `nutratenant_organization` database.
- APIGateway: `UpstreamService.ORGANIZATION_MANAGEMENT` +
  `organization_management_base_url` added (additive — no existing
  upstream removed, unlike the Observability cutover, since Organization
  is a genuinely new upstream, not a merge/replacement of existing ones).
  `route_service.py` registers one `/api/v1/organizations` route;
  `kong_admin_service.py`'s `KONG_ROUTE_PREFIX_MAP` maps it to
  `nutratenant-organization-management`. Every route-count-asserting test
  updated: `test_route_service.py` (11→12 total routes, +3 new tests for
  the organizations route specifically), `test_gateway_router.py` (5
  assertions), `test_kong_admin_service.py` (4 assertions),
  `test_proxy_router.py` (1 assertion). APIGateway's full suite: 110/110
  passing (was 107/107 before this change).

## Verification performed

- OrganizationManagement: 19/19 tests passing (fresh `uv sync` +
  `uv run pytest`, not inherited from a template), `ruff check`/
  `ruff format --check` clean.
- APIGateway: 110/110 tests passing after the cutover.
- `docker compose config --quiet`: clean (aside from pre-existing,
  unrelated `.env`-file-not-found warnings for services this change never
  touched).
- mypy: 10 errors, all in the exact same shape as `Tenent`'s own
  pre-existing, accepted gaps — `shared.observability.*` import-not-found
  (6, `main.py`/`health_router.py`, same root cause as `Tenent`/
  `APIGateway`/`ObservilityManagement` already have), `request_id.py`'s
  unused `type: ignore` + `"object" not callable` (copied verbatim from
  Tenent, which has the identical two errors in the identical file), and
  `conftest.py`'s `event_loop` fixture type-var complaint + one more unused
  `type: ignore` (same as Tenent's own `conftest.py`). None of these are
  new problems introduced by this service — every one already exists,
  unfixed, in Tenent today; fixing them here without fixing them there
  would just make the two services inconsistent for no benefit. A
  repo-wide fix (making `shared/` genuinely importable at runtime for
  every service, not just under pytest's `pythonpath`) is a separate,
  cross-cutting task, not something to solve once inside a single new
  service.

## Docker build/run — verified, one bug fixed

The Dockerfile was copied from `Tenent`'s pip-style multi-stage pattern
(`COPY --from=builder /root/.local /root/.local`), but the builder stage
runs `uv sync`, which installs into `/app/.venv`, not pip's user site.
`/root/.local` never exists in the builder, so the copy failed the build
outright — `Tenent`'s Dockerfile has the exact same bug and has apparently
never been built for real either.

Rewritten to match `IAM`/`APIGateway`'s current Dockerfile standard instead
of `Tenent`'s stale one: `uv` installed via the official binary layer (not
`pip install uv`), `COPY --from=builder /app/.venv /app/.venv` +
`PATH=/app/.venv/bin`, non-root `appuser` (uid/gid 10001), `HEALTHCHECK`
hitting `/health`, and `maintainer`/`service_name` labels — closing every
gap the `docker-verify` checklist flags (was: root user, no healthcheck, no
labels, and a build that didn't even complete).

Verified for real: `docker build` succeeds, container boots against a live
Postgres (`DATABASE_URL=postgresql+asyncpg://...`), `/health` returns 200,
and `docker inspect` reports `Health.Status: healthy` after the
`start-period`. `otel_init_failed: No module named 'shared'` logs at
startup (non-fatal, `enable_tracing` degrades gracefully) — same
`shared/observability` runtime-import gap already accepted for `Tenent`/
`APIGateway`/`ObservilityManagement` (see mypy note above); not something
to solve inside this service alone.
