# UserLifecycleManagement — Implementation Plan

**Status: Implemented.** Built per the plan below — 16/16 tests passing,
real Postgres migration applied, real Docker end-to-end verification done
against a genuinely running UserManagement container (see "Second pass:
what was actually built" at the bottom).

## Why this service, why now, and how it relates to UserManagement

`README.md` describes "the entire lifecycle of a user account from creation
to deletion": `POST/GET/PATCH/DELETE /users`, activate/deactivate/suspend,
plus richer operations `UserManagement` (built earlier this session,
`services/UserManagement/`) doesn't have — unsuspend, lock/unlock,
restore, onboard/offboard, and a `GET /users/{id}/status` aggregate view.

This is a near-total overlap with UserManagement's already-shipped CRUD
(`/api/v1/users`, 21 tests, wired into APIGateway). Raised this with the
user before planning further; resolved as: **this service owns the state
machine only, calling into UserManagement for the underlying user
record** — the same split this repo already documents for tenants
(`CLAUDE.md`'s Tenant Lifecycle States table): `TenantManagement` owns
authoritative CRUD + basic states, `TenantLifecycle` owns the richer state
machine (adds `locked`, drives all transitions, fires HTTP at TM to keep
it in sync — fire-and-log, TM failures non-fatal). This service is that
pattern applied to users: **`UserManagement` ≈ TM, `UserLifecycleManagement`
≈ TL.**

Concretely:
- `UserManagement` keeps everything it already has, unchanged: identity
  CRUD, its own `pending → active ⇄ suspended → deactivated` state machine,
  its own `/api/v1/users/{id}/activate|suspend|deactivate` endpoints. These
  remain valid to call directly for simple cases — this service is
  additive, not a replacement.
- `UserLifecycleManagement` is the richer, authoritative orchestrator for
  everything beyond that: `locked` (security hold, this-service-only,
  proxied to UserManagement as `suspended` — exact analogue of Tenant's
  `locked`), `restore` (undo a soft-delete), and `onboard`/`offboard` as
  named, audited variants of activate/deactivate.
- **One required companion change to UserManagement**: it currently has
  `soft_delete` but no undo. `restore` here needs
  `POST /api/v1/users/{id}/restore` on UserManagement (clear `deleted_at`)
  — a small, additive change, not a re-implementation. Call this out
  explicitly as a dependency before `restore` can work end-to-end.

## Scope conflicts resolved before writing this plan

1. **CRUD duplication** (`POST/GET/PATCH/DELETE /users`, `/activate`,
   `/deactivate`, `/suspend` in this README) — not re-implemented here.
   UserManagement already owns these, tested and deployed. This plan only
   covers what UserManagement doesn't have.
2. **Gateway routing** — this service's own endpoints must not reuse the
   literal `/users/{id}/...` paths from the README verbatim: APIGateway's
   `/api/v1/users` prefix already points at UserManagement, and the route
   registry does plain string-prefix matching with no path templating
   (same class of collision hit twice already this session — IAM's
   tenant-memberships and attributes renames, UserManagement's
   platform-invitations naming). This service mounts under its own
   `/api/v1/user-lifecycle` prefix instead — see Routers/Wiring below.
3. **`terminate` in Scope but not in the API list** — README's Scope
   bullet list says "Terminate users" but the API list has no `/terminate`
   endpoint. Read this as prose describing what `deactivate` already
   means (UserManagement's `DEACTIVATED` is already terminal, no
   transitions out) — not a distinct action. No new endpoint added for it.

## Architectural conventions to reuse (proven in IAM/OrganizationManagement/UserManagement)

- Repository/service/DI pattern, `PageResult`/cursor pagination
  (`repositories/base.py`, copied verbatim again).
- Domain layer: `enums.py` (`VALID_TRANSITIONS` dict-of-frozensets),
  `exceptions.py`, `commands.py`, `events.py` (dataclass-per-event).
- Audit trail: `LifecycleEvent` table, same shape as UserManagement's own
  `UserStatusHistory` / Tenent's `TenantLifecycleEvent`.
- **Cross-service HTTP call to UserManagement**: two existing patterns in
  this repo, and this service needs both, for different calls:
  - **Fail-fast** (`OrganizationManagement/app/infrastructure/clients/tenent_client.py`'s
    shape) for the calls where a failure must block the response — e.g.
    `restore` needs to *know* whether UserManagement's undelete actually
    succeeded before this service reports success.
  - **Fire-and-log** (`Tenent/app/infrastructure/clients/tenant_provisioning.py`'s
    shape, `except Exception: logger.warning(...)`, never raises) for
    syncing UserManagement's status after *this* service has already
    decided a transition is valid — matching TL's exact documented
    contract with TM ("fire-and-log — TM failures are non-fatal"). Accept
    the same known tradeoff TL/TM already accepts: if the sync call fails,
    this service's own record of the transition is still correct, but
    UserManagement's status column can drift out of sync until retried.
    Not solving that reconciliation problem here — same accepted gap as
    the Tenant side.
  - `UserLifecycleClient` (new, this service's own file): wraps both — a
    fail-fast `get_user`/`restore_user` pair used to read/confirm state,
    and a fire-and-log `sync_status(user_id, tenant_id, status)` used
    after every transition this service validates.

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `lifecycle_states` | user_id (plain — not FK, UserManagement owns the real row in a different service/DB), tenant_id, status, locked_reason (nullable), locked_by (nullable), created_at, updated_at | One row per user this service has ever acted on (created lazily on first transition, not on user creation — this service isn't notified of UserManagement's own `user.created` event in this pass; see Deferred below). |
| `lifecycle_events` | id, user_id, tenant_id, event_type, from_status, to_status, reason (nullable), performed_by (nullable), occurred_at | Append-only. Same shape as `UserStatusHistory`. `event_type` distinguishes `activate` vs `onboard` and `deactivate` vs `offboard` even when they cause the same status transition — matches the README listing them as separate actions. |

`domain/enums.py`: `LifecycleStatus` = `PENDING, ACTIVE, SUSPENDED, LOCKED, DEACTIVATED`.
`VALID_TRANSITIONS`:
- `PENDING → {ACTIVE}` (activate, onboard)
- `ACTIVE → {SUSPENDED, LOCKED, DEACTIVATED}` (suspend, lock, deactivate, offboard)
- `SUSPENDED → {ACTIVE, DEACTIVATED}` (unsuspend, deactivate)
- `LOCKED → {ACTIVE}` (unlock only — matches Tenant's `locked`: this-service-only, reversible via unlock, no other transition out)
- `DEACTIVATED → {}` (terminal, matches UserManagement's own terminal `DEACTIVATED`)

No `DELETED` state in this enum — deletion is UserManagement's own
`deleted_at`, not tracked as a status value here. `restore` doesn't depend
on this service's local state machine at all: it calls UserManagement
directly (`GET` the user, confirm `deleted_at` is set, call the new
`restore` endpoint, record a `lifecycle_event`) rather than trying to
intercept a delete this service was never notified of.

## Domain events (`domain/events.py`)

`LifecycleTransitioned` (user_id, tenant_id, event_type, from_status,
to_status, reason, performed_by) — one event shape covers every named
action (activate/deactivate/suspend/unsuspend/lock/unlock/onboard/offboard),
`event_type` carries the specific verb. No RabbitMQ publish this pass —
same reasoning as OrganizationManagement's deferral: no consumer exists for
lifecycle-specific events yet (IAM's `identity.events` exchange already has
a producer in UserManagement; adding a second, differently-shaped producer
for the same exchange without a concrete consumer is the speculative
infrastructure this repo's `TODO.md` conventions already argue against).
`lifecycle_events` itself is the audit trail, queryable directly.

## Services

- `lifecycle_service.py` — `LifecycleService`: one internal
  `_transition(user_id, tenant_id, to_status, event_type, reason, performed_by)`
  used by every public method below (validates `VALID_TRANSITIONS`, upserts
  `lifecycle_states`, writes `lifecycle_events`, fire-and-log syncs
  UserManagement via `UserLifecycleClient.sync_status`).
  - `activate` / `onboard` → both call `_transition(..., ACTIVE, event_type="activate"|"onboard")`
  - `deactivate` / `offboard` → both call `_transition(..., DEACTIVATED, event_type="deactivate"|"offboard")`
  - `suspend` → `_transition(..., SUSPENDED, event_type="suspend")`
  - `unsuspend` → `_transition(..., ACTIVE, event_type="unsuspend")` (only valid from `SUSPENDED`; `activate`/`onboard` only valid from `PENDING` — same `to_status`, different allowed `from_status`, enforced by checking `VALID_TRANSITIONS[from_status]` contains `to_status` either way, so no extra logic needed beyond the existing table)
  - `lock(reason, locked_by)` → `_transition(..., LOCKED, event_type="lock")`, stores `locked_reason`/`locked_by`
  - `unlock` → `_transition(..., ACTIVE, event_type="unlock")`, clears `locked_reason`/`locked_by`
  - `restore(user_id, tenant_id, performed_by)` → fail-fast calls
    `UserLifecycleClient.get_user` (404 → `UserNotFoundError`, not-deleted →
    `UserNotDeletedError`), fail-fast calls `restore_user`, then records a
    `lifecycle_events` row (`event_type="restore"`) — does **not** go
    through `_transition`/`VALID_TRANSITIONS` since it isn't part of the
    local state machine.
  - `get_status(user_id, tenant_id)` → fail-fast `get_user` (for
    UserManagement's own status + `display_name`/`deleted_at`) merged with
    this service's local `lifecycle_states` row (`locked_reason` if any) +
    most recent `lifecycle_events` row — the aggregate view
    `GET .../status` returns.

## Routers (`api/v1/lifecycle_router.py`, mounted at `/api/v1/user-lifecycle/{user_id}`)

All `X-Tenant-ID` scoped:
- `POST .../activate` · `POST .../onboard` (both PENDING→ACTIVE)
- `POST .../deactivate` · `POST .../offboard` (both →DEACTIVATED)
- `POST .../suspend` · `POST .../unsuspend`
- `POST .../lock` (body: `reason`, `locked_by`) · `POST .../unlock`
- `POST .../restore`
- `GET .../status` (the aggregate view)

Not `/api/v1/users/{id}/...` as the README literally shows — see Scope
conflict #2 above.

## Wiring (once implemented)

- `docker-compose.yml`: new `user-lifecycle-management` service, port
  **8024** (next unused after UserManagement's 8023). Needs Postgres +
  a `USER_MANAGEMENT_BASE_URL` env var pointing at UserManagement's
  container (`http://user-management:8000`) — no RabbitMQ needed this pass
  (no publish, per Domain events above).
- `infrastructure/postgres/init.sql`: add `nutratenant_user_lifecycle`.
- **UserManagement companion change**: add
  `POST /api/v1/users/{id}/restore` (clears `deleted_at`) — needed before
  this service's `restore` can work at all. Small: one repository method
  (`UserRepository.restore`), one service method, one route, tests.
- APIGateway: new `UpstreamService.USER_LIFECYCLE_MANAGEMENT` +
  `user_lifecycle_management_base_url`, route registry entry for
  `/api/v1/user-lifecycle` (does not collide with UserManagement's
  `/api/v1/users` — different literal prefix, by design).

## Verification (once implemented)

1. `uv sync`, `uv run pytest -v` — full suite green, including a test that
   `lock` is reachable only from `ACTIVE` and only reversible via `unlock`
   (mirrors `test_deactivate_is_terminal`-style tests already written for
   UserManagement).
2. `alembic revision --autogenerate` against real local Postgres, `upgrade
   head`.
3. `ruff`/mypy clean, same accepted-gap shape as every sibling service.
4. Real Docker end-to-end: boot this service **and** UserManagement
   together, create a user via UserManagement, drive it through
   `lock → unlock` via this service, confirm UserManagement's own status
   column actually flips to `suspended` and back to `active` (the
   fire-and-log sync actually landing, not just logged as attempted) —
   the same class of "don't trust the fire-and-log path without checking"
   lesson UserManagement's own RabbitMQ verification surfaced this
   session.
5. Confirm `restore` end-to-end after implementing UserManagement's
   companion `/restore` endpoint: delete a user via UserManagement, restore
   it via this service, confirm `deleted_at` is cleared via a separate
   `GET` against UserManagement.

## Deferred (not this pass)

- This service doesn't consume UserManagement's `user.created` RabbitMQ
  event to lazily create `lifecycle_states` rows ahead of first use —
  rows are created lazily on first transition instead. Revisit if a real
  need for pre-populated lifecycle rows (e.g. reporting on users who've
  never had any transition) shows up.
- Onboarding/offboarding are modeled as named transition variants, not
  multi-step workflows with their own state machine (no evidence in the
  README of discrete steps beyond a single POST) — revisit only if a
  concrete multi-step requirement appears.

## Second pass: what was actually built

Followed the plan above almost exactly. Notable deltas:

**1. UserManagement's companion `restore` endpoint was added as planned**,
not deferred: `UserRepository.restore`, `UserService.restore`,
`POST /api/v1/users/{id}/restore`, a new `UserNotDeletedError` /
`UserRestored` event, 3 new tests (24/24 total, up from 21). Deliberately
not routed through the existing `UserDep` dependency — that helper's
default lookup excludes soft-deleted users, which is exactly the case this
endpoint needs to reach, so it takes a plain `user_id: UUID` path param
instead.

**2. Two bugs caught before they became real, both in test infrastructure
rather than the shipped service code**:
   - mypy: `tests/conftest.py`'s `fake_client` fixture was decorated with
     `@pytest_asyncio.fixture` despite being a plain sync function —
     wrong decorator for a non-async fixture, caught as a genuine new
     `type-var` error beyond this repo's accepted 10-error baseline gap.
     Fixed by using `@pytest.fixture` instead.
   - `FakeUserLifecycleClient.sync_status` (the test double for
     UserManagement) initially set the remote user's status to the literal
     `to_status` value passed in, including `"locked"` — but
     UserManagement has no concept of `locked`, only pending/active/
     suspended/deactivated. The real `UserLifecycleClient.sync_status`
     already maps `LOCKED → suspend` correctly via `_SYNC_ENDPOINT`; the
     fake just didn't replicate that mapping, so
     `test_lock_then_unlock` caught the mismatch immediately
     (`'locked' == 'suspended'` assertion failure) before it could mask a
     real bug elsewhere. Fixed the fake to mirror the same proxy mapping.

**3. Confirmed working end-to-end against a real running UserManagement
container** (not just the in-memory fake): built both images, ran them on
the shared `backend` network, created + activated a real user via
UserManagement, then drove it through UserLifecycleManagement's
`lock → unlock` and confirmed UserManagement's own `status` column
genuinely flipped `active → suspended → active` via the real fire-and-log
HTTP sync (not just logged as attempted). Separately confirmed `restore`:
deleted a user via UserManagement, restored it via UserLifecycleManagement,
confirmed `deleted_at` cleared via an independent `GET` against
UserManagement.

Everything else (data model, domain events, `_transition`-backed service
methods, `/api/v1/user-lifecycle` routing to avoid the `/api/v1/users`
collision, the two-HTTP-client-pattern split) matched the plan as written.
