# IAM — Implementation Notes

**Status: Implemented.** Every entity in root `CLAUDE.md`'s ownership list
(Users, Roles, Permissions, Groups, Memberships, Entitlements, Attributes,
Access Reviews) is live; 43/43 tests pass; wired into `docker-compose.yml`,
APIGateway's route registry, and ObservilityManagement's Prometheus scrape
config + alert rules. Four real, previously-undiscovered bugs were found
and fixed during this build (see "Bugs found" below) — two in IAM itself,
two in the wider observability stack that blocked verifying IAM's own
metrics pipeline.

## What this is

Per root `CLAUDE.md`, `services/IAM` is "the first fully active
implementation" in this repo, but on this branch it was almost entirely an
empty scaffold: `main.py` was the FastAPI cookiecutter default, all 8
`api/v1/*_router.py` files were 0 bytes, 6 of 7 `models/*.py` files were 0
bytes, all schemas but one were 0 bytes, `domain/{enums,exceptions}.py`
were 0 bytes, `repositories/`/`services/` were empty stub packages, and
`alembic/versions/` had never had a revision generated. Only
`core/config.py` and `models/user_projection.py` (+ its schema) had real
content. This build fills in every stub, following the conventions already
established by `services/OrganizationManagement`/`services/Tenent` — the
only two fully-built sibling services in this repo.

## Design Decisions

1. **Users are read-only.** IAM's own `README.md` documents
   `POST/PATCH/DELETE /users`, but `UserProjection`'s docstring says it must
   only ever be written via async `user.created/updated/deleted` events
   from a User Service that doesn't exist yet anywhere in this repo. Built
   only `GET /users` and `GET /users/{id}` against the projection table;
   write endpoints are intentionally omitted. Confirmed with the user
   before building.

2. **No RabbitMQ consumer this pass.** The projection table, model, and
   read endpoints exist; the event consumer that would populate
   `UserProjection` in production is deferred. Tests seed the table
   directly via the `db_session` fixture. Confirmed with the user.

3. **No cross-service tenant validation.** Unlike `OrganizationManagement`'s
   `TenentClient` call to Tenent at creation time, IAM trusts the
   `X-Tenant-ID` header as-is for every tenant-scoped write — no synchronous
   HTTP dependency on Tenent, no new failure mode. Confirmed with the user.

4. **Tenant Memberships live at `/api/v1/tenant-memberships/{tenant_id}/members`,
   not README's literal `/tenants/{tenant_id}/members`.** APIGateway's route
   registry (`route_service.py`) does plain string-prefix matching with no
   path templating, and Tenent already owns the `/api/v1/tenants` prefix
   for its own tenant CRUD. Any request under `/api/v1/tenants/...` would
   match Tenent's rule first and never reach IAM — registering IAM's literal
   documented path would have silently misrouted every tenant-membership
   call to Tenent. Renamed to a non-colliding prefix instead of teaching the
   gateway path-template awareness for one endpoint.

5. **`EntityStatus` (`active`/`deleted`) is one shared enum**, reused by
   Role, Permission, and Group — not three near-identical two-value enums.
   `MembershipStatus`, `AttributeValueType`, `EntitlementStatus`, and
   `AccessReviewStatus` are genuinely different value sets and stay
   separate.

6. **Many-to-many association tables (`role_permissions`, `user_roles`,
   `group_memberships`) are a new pattern in this repo** — neither
   OrganizationManagement nor Tenent defines any `relationship()`/`Table()`/
   `secondary=`. Used plain composite-PK tables with real FKs
   (`ondelete="CASCADE"`) between fully-IAM-owned, synchronously-consistent
   entities (role↔permission, group↔group_membership), but **plain
   `user_id` columns, not FKs to `user_projections.id`** — Users are
   eventually-consistent projection data (same reasoning as `tenant_id`
   elsewhere in this repo), so a hard FK could break on an assignment made
   just before a projection sync lands, and historical assignments should
   survive a user's projection row being deleted.

7. **`Attributes` are hard-deleted; Roles/Permissions/Groups/Entitlements
   are soft-deleted.** Attributes are simple key-value ABAC data, not an
   audited business entity — no `deleted_at` column, no history to
   preserve.

8. **`entitlements` gets a detail + delete endpoint beyond README's
   list/create-only spec**, for CRUD symmetry with every other resource in
   this service. Same for `access_reviews`, which isn't in README's
   endpoint table at all but is in root `CLAUDE.md`'s ownership list —
   built a minimal create/list/detail/record-decision shape.

9. **`security.py` and the ABAC policy evaluation engine are out of
   scope.** No Authentication service exists yet to integrate with
   (`Implementation-order.md` priority 5, not built) and ABAC Policy
   Management/Evaluation are separate, later, not-yet-built services
   (`Implementation-order.md` priorities 7–8). This build is IAM's data
   layer — identities, roles, permissions, groups, attributes — that those
   future services will read from, matching the `Authorization`/
   `AbacPolicyManagement` stub READMEs' own stated separation of concerns
   ("IAM Service: Stores identities, roles, permissions, attributes" /
   "Authorization Service: Evaluates policies and makes access decisions").

## Bugs found and fixed (pre-existing, not introduced by this build)

1. **`models/user_projection.py` defined its own second, disconnected
   `Base(DeclarativeBase)`** instead of importing the shared one from
   `infrastructure/database/base.py`. Two unrelated declarative bases meant
   `Base.metadata.create_all()` in tests would never have created
   `user_projections` once other models existed. Fixed: import the shared
   `Base`.

2. **`infrastructure/database/dependencies.py`'s `get_db()` never
   committed.** It only did `async with SessionLocal() as session: yield
   session` — no `commit()`, no `rollback()`. Every write in a real running
   container would silently succeed at the HTTP layer (service/repository
   `flush()` makes it visible within that request's own transaction) and
   then be discarded the moment the session closed, since each request gets
   a fresh session/transaction. **This was caught by real end-to-end Docker
   verification, not by the test suite** — the test suite's `db_session`
   fixture shares one session across setup and assertions within a test, so
   the missing commit was invisible there. Confirmed via: `POST
   /api/v1/roles` returned 201 with a real row, then `GET /api/v1/roles`
   immediately after (a *different* request, a *different* session) showed
   `total: 0` — the row had already been rolled back on session close.
   Fixed to match `OrganizationManagement`/`Tenent`'s identical pattern
   (commit on success, rollback + re-raise on exception).

3. **`ObservilityManagement/prometheus/alerts/infra_alerts.yml`'s
   `OTelCollectorHighMemory` alert referenced `humanizeBytes`**, which
   isn't a real Prometheus template function (the correct one is
   `humanize1024`). This made the *entire* Prometheus container fail to
   start — a bad rule file is a hard config-load error, not a
   per-rule skip, so this one broken alert (in a file with no connection
   to IAM at all) was taking down every rule group and every scrape target
   for the whole platform. Found while verifying IAM's own Prometheus
   scrape target actually works. Fixed: `humanize1024` + `B` suffix,
   matching the convention already used by the sibling `humanizeDuration`/
   `humanizePercentage` calls elsewhere in the same file.

4. **`ObservilityManagement/otelcol/config.yaml`'s `loki` exporter used a
   `labels:` config key that doesn't exist in collector v0.105.0**
   (`otel/opentelemetry-collector-contrib:0.105.0`, per `docker-compose.yml`).
   This crash-looped the entire OTel Collector container — no traces,
   metrics, or logs from *any* service (not just IAM) could reach
   Tempo/Prometheus/Loki. Also found while verifying IAM's own
   observability wiring. The static `labels:` mapping was deprecated in
   favor of `loki.resource.labels`/`loki.attribute.labels` hint attributes
   set via a processor; fixed by extending the existing `resource`
   processor and adding a new `attributes/loki_labels` processor to the
   logs pipeline, removing the invalid exporter config block.

Both #3 and #4 are pre-existing bugs untouched by this build's own diffs
(confirmed via `git diff`/`git status` before fixing) — the observability
stack had apparently never been booted for real before. Fixed here because
verifying IAM's own metrics/logs pipeline requires a working Prometheus and
OTel Collector; every other service in this repo benefits from the fix too.

## ObservilityManagement wiring

- `prometheus/prometheus.yml`: added a direct-scrape `iam` job (matching
  the existing `api-gateway`/`tenent` fallback-scrape pattern — the "OTel
  pipeline down" fallback).
- `prometheus/alerts/api_alerts.yml`: added `iam` to the `ServiceDown`
  alert's job regex.
- No changes needed to `otelcol/config.yaml`'s pipelines (already generic
  OTLP ingestion — any service sending to `otel-collector:4317` is picked
  up automatically), the Grafana dashboard (`service_overview.json` uses a
  dynamic `label_values(...)` template query, not a hardcoded service
  list), Promtail (auto-discovers all Docker containers via
  `docker_sd_configs`), or the recording rules / business alert rules
  (already grouped generically `by (job, ...)` / `by (service, ...)`).
- Verified for real: brought up `postgres` + `otel-collector` + `prometheus`
  + `iam` via `docker compose up`, confirmed `up{job="iam"} == 1` via
  Prometheus's HTTP API, and confirmed the `ServiceDown`/
  `OTelCollectorHighMemory` rules both evaluate `health: ok` (previously
  the whole rule file failed to load).
- **Not done**: `organization-management` is *also* missing from
  `prometheus.yml`'s direct-scrape list (a gap from before this session,
  unrelated to IAM) — flagged, not fixed, since it's out of scope for this
  task.

## Housekeeping fixes bundled into this pass

- `pyproject.toml` was missing `sqlalchemy`/`pydantic-settings` as explicit
  dependencies (present only transitively via `alembic`/`fastapi` in
  `uv.lock`) and had **no dev/test toolchain at all** — no `pytest`,
  `ruff`, `mypy`, `aiosqlite` anywhere in the lockfile. `uv run
  pytest`/`ruff`/`mypy` could not have run for this service before this
  change. Added explicit deps, the observability stack
  (`opentelemetry-*`, `prometheus-client`) matching
  `OrganizationManagement`'s shape, and a `[dependency-groups] dev` section.
- `alembic/env.py` was the unmodified cookiecutter (`target_metadata =
  None`) — wired to `Base.metadata` matching
  `OrganizationManagement/alembic/env.py`'s async-engine pattern. Generated
  and applied the **first-ever** IAM migration, covering `user_projections`
  + 10 new tables.
- `infrastructure/postgres/init.sql` never created `nutratenant_identity`
  — IAM's own `database_url` default pointed at a database that would
  never have existed. Added the `CREATE DATABASE` guard matching the other
  four entries.
- `.env.example` was 0 bytes — populated to mirror `config.py`'s
  `Settings` fields 1:1.
- A mypy quirk (not a repo-specific bug, but new to this codebase): a
  method literally named `list` shadows the builtin `list` type for
  `list[X]` annotations appearing *later in the same class body* under
  `from __future__ import annotations`. Hit this in `RoleRepository`/
  `GroupRepository`/`RoleService`/`GroupService`, which each combine a
  paginated `.list()` method with other `list[X]`-returning helpers
  (`list_permissions`, `list_members`, etc.) — none of
  OrganizationManagement's classes happen to combine both in one class, so
  it was never hit there. Fixed by moving each class's `.list()` to be the
  last method defined, not by renaming it (keeping the established
  `.list()` pagination convention).
- Added `app/middleware/request_id.py` and `app/core/logging.py` (neither
  existed) and `app/core/openapi.py`, matching every sibling service's
  structured-logging/request-ID/OpenAPI-tags conventions — `main.py`
  needed them for the same `create_app()`/`lifespan()` shape every other
  service uses.

## Verification performed

- IAM: 43/43 tests passing (fresh `uv sync --all-groups` +
  `uv run pytest`), `ruff check`/`ruff format --check` clean. mypy: 10
  errors, identical shape/count to every sibling service's accepted gap
  (`shared.observability.*` import-not-found ×6, `request_id.py` ×2,
  `conftest.py` ×2) — no new errors introduced by this service.
- Alembic: `alembic revision --autogenerate` against a real local Postgres
  correctly detected all 11 tables (including the 3 new association
  tables); `alembic upgrade head` applied cleanly; verified via `\dt`
  against the live database.
- Docker: `docker build` succeeds; container boots against real Postgres
  via `docker compose up --build iam`, `/health` returns 200,
  `docker inspect` reports `Health.Status: healthy`. Exercised a real
  write-then-read cycle (`POST /api/v1/roles` → `GET /api/v1/roles`)
  against the actual running container — this is exactly what caught the
  `get_db()` missing-commit bug above.
- APIGateway: 120/120 tests passing after the cutover (was 115 before —
  10 new IAM-specific route-resolution tests added, 5 existing
  route-count/upstream-count assertions updated from 12→19 total routes
  and 4→5 unique upstreams). `docker compose up --build iam` verified
  end-to-end through compose's own network/env wiring, not just a
  standalone `docker run`.

## Known pre-existing gaps (not fixed here, out of scope)

- `docker compose config` (no service argument) fails outright — several
  *other* services (`TenantManagement`, `TenantLifecycle`,
  `TenantProvisioning`, `TenantIsolation`) reference `.env`/`.env.example`
  files that don't exist on disk, and Compose treats a missing `env_file`
  as fatal for the whole manifest, not per-service. This predates IAM
  entirely. Targeting a specific service (`docker compose up iam`) works
  fine since Compose only resolves that service's own dependency graph.
  Repo-wide fix (creating the missing `.env`/`.env.example` files, or
  removing those `env_file:` references) is a separate, cross-cutting task.

## Third pass: IAM checklist review findings, fixed

Ran the `/IAM-service` skill's review checklist against this service.
Two real, concrete findings came out of it; both fixed this pass (a third
finding — no caller authentication anywhere in the request path — is a
genuine current-state risk but isn't fixable within IAM alone: it's
blocked on the not-yet-built Authentication Service, priority 5 in
`Implementation-order.md`. Left as an explicit, documented risk rather
than worked around).

**1. A real, previously undetected routing bug: `/api/v1/users/{id}/roles`
was unreachable via the gateway.** When `/api/v1/users` was repointed to
UserManagement earlier this session, the attribute-assignment sub-resource
was renamed to avoid the collision (`/user-attributes/{id}`) — but
`roles_router.py`'s user<->role assignment endpoints define their path
inline (`@router.post("/users/{user_id}/roles")`) rather than via a
router-level `prefix=`, so the grep used to find affected routes at the
time missed it entirely. Confirmed broken by resolving the path through
`RouteService` directly: it returned `UpstreamService.USER_MANAGEMENT`,
not `IAM`. Fixed with the same rename pattern already used twice: mounted
at `/user-roles/{user_id}` instead. Updated `roles_router.py`,
`test_roles.py`, this service's `README.md`, and APIGateway's
`route_service.py`/`kong_admin_service.py`/tests (route count 23→24, IAM's
route count 7→8). 43/43 IAM tests and 130/130 APIGateway tests still pass.

**2. No audit trail for authorization-changing operations.** Role
assignment/unassignment, role<->permission linkage, group membership,
tenant membership, and entitlement grant/revoke recorded nothing —
inconsistent with this repo's own established pattern (`Tenent`'s
`TenantLifecycleEvent`, `OrganizationManagement`'s `OrganizationEvent`,
`UserManagement`'s `UserStatusHistory`, `UserLifecycleManagement`'s
`LifecycleEvent` all built a local audit table before any dedicated Audit
Logging Service existed). Fixed: new `AuditEvent` model/repository/schema/
service, a new `GET /api/v1/audit-events` endpoint (tenant-scoped,
`subject_user_id`/`resource_type` filters, cursor pagination), and every
grant/revoke method across `RoleService`/`GroupService`/
`MembershipService`/`EntitlementService` now records an event. Each
write endpoint accepts an optional `performed_by` field (body for
POST/create, query param for DELETE), recorded as `actor_id` — **caller-
supplied and unverified**, same caveat as finding #3 below; not a
substitute for real authentication, just a courtesy trail until one
exists. 8 new tests, all passing; full suite 51/51. Confirmed for real
against a running container + Postgres: assigned a role via the (now
fixed) `/user-roles/{id}` endpoint with a `performed_by` actor, then
confirmed the exact event (`role.assigned`, correct `resource_id`,
`subject_user_id`, `actor_id`) via a separate `GET /audit-events` call —
not just trusting the write path succeeded silently.

**3. No caller authentication anywhere (documented, not fixed).** Every
endpoint trusts `X-Tenant-ID` at face value; `secret_key` in `config.py`
is dead config, never used to sign or verify anything. This is
architecturally expected right now — Authentication Service doesn't exist
yet — but it means this service is not currently safe to expose to real
traffic: anyone who can set an arbitrary `X-Tenant-ID` has full read/write
access to that tenant's roles, permissions, memberships, and attributes.
Flagging explicitly here so it isn't mistaken for an oversight when
Authentication Service is eventually built — closing this gap belongs
there, not in IAM.

Also fixed in passing: `services/IAM/app/__init__.py`,
`app/core/__init__.py`, and `app/domain/__init__.py` never existed (unlike
every sibling service), which made `uv run mypy .` fail outright with
"Source file found twice" once enough files existed to trigger the
ambiguity. Added the three missing empty `__init__.py` files — unrelated
to the audit trail work, just discovered while running this pass's
quality gate.
