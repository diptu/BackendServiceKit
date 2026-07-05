# UserManagement — Implementation Plan

**Status: Implemented.** Built per the plan below — 21/21 tests passing,
real Postgres migration applied, real Docker + RabbitMQ end-to-end
verification done (see "Second pass: what was actually built" at the
bottom for exact deltas from this plan, including two real bugs found and
fixed along the way).

## Why this service, why now

Per `Implementation-order.md`, User Management is priority 4 — directly
after IAM (✅ completed) and Organization Management (🚧 in progress). It is
also the missing piece IAM has been waiting on since it was built: IAM's
`UserProjection` model (`services/IAM/app/models/user_projection.py`) is a
read-only materialized view that's supposed to be populated by
`user.created`/`user.updated`/`user.deleted` events from "the User
Service" — a service that didn't exist yet when IAM was built. IAM's own
config already declares `rabbitmq_exchange: str = "identity.events"`
(`services/IAM/app/core/config.py`), and its `TODO.md` explicitly defers
"the consumer that would populate it in production." **This service is
that producer.**

## Scope conflict resolved before writing this plan

`README.md` lists `tenant_memberships` under "Owns" and documents
`POST/DELETE /tenants/{tenant_id}/members`. **IAM already owns this
exact concept** — `services/IAM/app/models/membership.py::TenantMembership`
(a user's membership within a tenant, distinct from group/org membership),
exposed at `/api/v1/tenant-memberships/{tenant_id}/members`, fully built and
tested. Confirmed with the user: **this service's plan omits
tenant_memberships entirely** — IAM's implementation stands, and this
README's claim is superseded. Scope here is `users`, user status, and
platform-level invitations only.

**Also worth naming explicitly**: this service's invitations
(`POST /invitations`) are a *different* concept from
`OrganizationManagement`'s invitations
(`POST /organizations/{id}/invitations`, already built). This service's
invitations onboard a brand-new person onto the *platform* (accepting one
creates a `User` row, with no organization or role attached).
OrganizationManagement's invitations add an *already-known* `user_id` to a
*specific organization* with a role. They compose (platform invite → user
exists → separate org invite → org membership) rather than overlap.

**No credentials owned here.** Authentication Service is a separate,
later, not-yet-built service (`Implementation-order.md` priority 5). This
service owns identity/profile data only — no password hashes, no MFA
secrets, no sessions. Same boundary IAM's `UserProjection` docstring already
enforces on itself.

## Architectural conventions to reuse (proven in IAM/OrganizationManagement — do not reinvent)

- **Repository/service/DI pattern**: `BaseRepository`/`PageResult`/
  `encode_cursor`/`decode_cursor` copied verbatim from
  `OrganizationManagement/app/repositories/base.py` (byte-identical to
  Tenent's and IAM's). Per-entity repos follow the `Filter` dataclass +
  `create`/`save`/`soft_delete`/`get_by_id`/`count`/`list` shape.
  DI composition via `app/api/v1/dependencies.py`
  (`get_db` → `get_<x>_service` → `Annotated[...] = Depends(...)` aliases,
  `TenantIdDep` reading the required `X-Tenant-ID` header) — never a bare
  `_svc(db)` closure.
- **Domain layer**: `domain/enums.py`, `domain/exceptions.py` (plain
  `Exception` subclasses carrying relevant IDs), `domain/commands.py`
  (dataclass-per-mutation, services never take the Pydantic request schema
  directly), `domain/events.py` (dataclass-per-event, `event_id`/
  `timestamp` defaults — Tenent's exact shape).
- **Audit trail**: a `UserStatusHistory` table mirroring
  `Tenent/app/models/lifecycle_event.py` (append-only, `from_status`/
  `to_status`/`reason`/`performed_by`/`occurred_at`) — this table is a
  closer match to Tenent's *lifecycle*-event shape than
  OrganizationManagement's generic `OrganizationEvent`, since user status
  transitions are exactly what Tenent's table was designed to record.
- **Invitation security**: `secrets.token_urlsafe(32)` raw token,
  SHA-256 `token_hash` persisted (never the raw token), accept flips status
  atomically in the same transaction as the `User` row insert — copied from
  `OrganizationManagement/app/services/invitation_service.py`, including
  its `_as_aware_utc()` SQLite/Postgres timezone-comparison fix (SQLite
  drops tzinfo on `DateTime(timezone=True)` columns; Postgres doesn't —
  hit this exact bug building OrganizationManagement's invitations, fix it
  here from the start rather than rediscovering it).
- **RabbitMQ publisher**: `Tenent/app/infrastructure/messaging/publisher.py`'s
  `RabbitMQPublisher`/`NullPublisher` pair (fire-and-log, never blocks the
  caller, degrades to a no-op if RabbitMQ is unreachable) — copied as-is.
  Unlike OrganizationManagement's decision to skip RabbitMQ (no consumer
  anywhere), **this service has a concrete, already-declared consumer
  target** (IAM's `identity.events` exchange), so the publisher is
  in scope here even though IAM's consumer side remains separately deferred
  (documented in IAM's own `TODO.md` — wiring IAM to actually process these
  events is *not* part of this service's work, just made possible by it).

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `users` | id, tenant_id (plain — projection, not FK, per the `tenant_id` convention every service in this repo follows), email, first_name, last_name, status, created_at, updated_at, deleted_at | unique(tenant_id, email). Soft-deleted. No credentials. |
| `user_status_history` | id, user_id (FK CASCADE — fully owned by this service, unlike cross-service `user_id` refs elsewhere), from_status, to_status, reason (nullable), performed_by (nullable), occurred_at | Append-only, mirrors `TenantLifecycleEvent`. |
| `user_invitations` | id, tenant_id, email, token_hash (unique), invited_by, status, expires_at, accepted_at (nullable), revoked_at (nullable), created_at, updated_at | Same shape as `OrganizationInvitation` minus `organization_id`/`role`. |

`domain/enums.py`: `UserStatus` (`pending` → `active` ⇄ `suspended` →
`deactivated`, terminal) with a `VALID_TRANSITIONS` dict-of-frozensets
(Tenent's/OrganizationManagement's exact shape); `InvitationStatus`
(pending/accepted/expired/revoked — identical to OrganizationManagement's).

## Domain events (`domain/events.py`)

`UserCreated`, `UserUpdated`, `UserStatusChanged` (from_status/to_status/
reason), `UserDeleted`, `InvitationCreated`, `InvitationAccepted`,
`InvitationRevoked`. Each published to RabbitMQ (`routing_key` = event class
name in snake_case, e.g. `user.created`) via the copied `RabbitMQPublisher`,
**and** recorded to `user_status_history` when the event is a status
transition specifically (creation/update/deletion don't need a history row
— only status changes do, matching the table's narrower purpose).

## Services

- `user_service.py` — `UserService`: `create` (raises on duplicate
  tenant+email), `get`, `list`, `update`, `activate`/`suspend`/`deactivate`
  (each validates the transition against `VALID_TRANSITIONS`, writes a
  `user_status_history` row, publishes `UserStatusChanged`), `delete`
  (soft-delete, publishes `UserDeleted`).
- `invitation_service.py` — `InvitationService`: `create_invitation`
  (generates token, returns raw token once), `accept_invitation` (hash
  lookup, status/expiry check via `_as_aware_utc`, creates the `User` row
  via `UserService.create`, marks invitation accepted — one transaction,
  publishes `UserCreated` + `InvitationAccepted`), `revoke_invitation`.

## Routers (`api/v1/users_router.py`, `api/v1/invitations_router.py`)

- `POST/GET /users` · `GET/PATCH/DELETE /users/{id}` — all `X-Tenant-ID`
  scoped, resolved via `get_user_or_404(id, tenant_id)` together (never a
  bare UUID lookup — same cross-tenant-404-not-403 rule as every other
  service in this repo).
- `POST /users/{id}/activate` · `POST /users/{id}/suspend` ·
  `POST /users/{id}/deactivate` — each a thin wrapper over
  `UserService`'s corresponding transition method; invalid transitions
  (e.g. activating an already-deactivated user) return 409 via a new
  `InvalidUserTransitionError`, mirroring Tenent's
  `InvalidOrganizationTransitionError`-equivalent pattern (`OrganizationManagement`'s
  is named `InvalidOrganizationTransitionError`; this service's would be
  `InvalidUserStatusTransitionError`).
- `GET /users/{id}/status-history` — paginated, mirrors
  OrganizationManagement's `GET /organizations/{id}/events` shape.
- `POST /invitations` · `GET /invitations/{id}` ·
  `POST /invitations/{id}/revoke` — `X-Tenant-ID` scoped (a platform
  invitation still belongs to one tenant).
- `POST /invitations/accept` — **not** tenant-scoped (matches
  OrganizationManagement's `POST /invitations/accept`: the token alone
  identifies everything; no header required to accept).

## Wiring (once implemented)

- `docker-compose.yml`: new `user-management` service, port **8023** (next
  unused after IAM's 8022). Needs Postgres **and** RabbitMQ (the first of
  these three services to need messaging since Tenent) —
  `RABBITMQ_URL`/`RABBITMQ_EXCHANGE=identity.events` env vars, matching
  IAM's already-declared exchange name exactly so the (future) consumer
  doesn't need reconfiguring.
- `infrastructure/postgres/init.sql`: add `nutratenant_user` database
  (this repo's existing gap-detection pattern already caught a missing
  `nutratenant_identity` entry once during IAM's build — check this one
  proactively rather than rediscovering the same bug).
- APIGateway: new `UpstreamService.USER_MANAGEMENT` + `user_management_base_url`,
  route-registry entries for `/api/v1/users` and `/api/v1/invitations`
  (the latter must not collide with OrganizationManagement's own
  `/api/v1/invitations` prefix — **it will**, since both services mount an
  `invitations_router` at the same path. Resolve before implementing: either
  this service's platform invitations move to a distinct prefix, e.g.
  `/api/v1/platform-invitations`, or OrganizationManagement's stays at
  `/api/v1/organizations/{id}/invitations` only with no top-level
  `/api/v1/invitations/accept` alias — needs a decision at implementation
  time, flagged here rather than guessed).

## Verification plan (once implemented)

1. `uv sync`, `uv run pytest -v` — per-entity test files mirroring
   OrganizationManagement's style; full suite green.
2. `alembic revision --autogenerate` against real local Postgres, `upgrade
   head`, verify via `\dt`.
3. `ruff check`/`ruff format --check` clean; mypy: expect the same 10-error
   accepted-gap shape every sibling service has (`shared.observability.*`
   import-not-found ×6, `request_id.py` ×2, `conftest.py` ×2) — treat any
   *other* mypy error as new and fix it before calling this done.
4. Real end-to-end: `docker compose up --build user-management` +
   `rabbitmq`, confirm `/health` returns 200 and `docker inspect` reports
   `healthy`, then a genuine write-then-read cycle (create user → separate
   request lists it) — the `get_db()` missing-commit bug from IAM was only
   caught this way, not by the test suite.
5. Confirm a message actually lands on the `identity.events` exchange after
   creating a user (e.g. via RabbitMQ's management UI or `rabbitmqadmin`) —
   don't just trust that `RabbitMQPublisher.publish()` was called; the
   fire-and-log `except Exception: logger.warning(...)` swallows failures
   silently by design, so a wiring mistake (wrong exchange name, wrong
   routing key) would otherwise go unnoticed.

## Second pass: what was actually built

Followed the plan above almost exactly. Three real deltas worth recording:

**1. A second routing collision the plan missed.** APIGateway's Kong
mapping and route registry already pointed `/api/v1/users` at IAM (its
`GET`-only `UserProjection`), not just the `tenant_memberships` collision
this plan already called out. Since UserManagement's CRUD needed that same
path, and the route registry does plain string-prefix matching (no path
templating, first-match-wins), asked the user: **repoint
`/api/v1/users` to UserManagement** — it's now the authoritative service,
IAM's `UserProjection` was always meant as an internal read cache. This
had a knock-on effect: IAM's `/users/{user_id}/attributes` sub-resource
would have been silently swallowed by the same `/api/v1/users` prefix
(the registry has no notion of "this specific sub-path routes elsewhere"),
so it was renamed to `/api/v1/user-attributes/{user_id}` — same rename
precedent as IAM's own `tenant_memberships` fix. Updated: IAM's
`attributes_router.py`, `README.md`, `test_attributes.py` (43/43 still
pass); APIGateway's `route_service.py`, `kong_admin_service.py`,
`domain/enums.py`, `core/config.py`, and three test files (123/123 still
pass, route count 19 → 21: `+/api/v1/platform-invitations`,
`+/api/v1/user-attributes` as its own explicit registry entry).

**2. A real bug in the RabbitMQ publisher, caught only by real Docker +
RabbitMQ verification** (exactly per point 5 above — the test suite
wouldn't have caught this since it runs against `NullPublisher`).
`_default_serializer` in `infrastructure/messaging/publisher.py` (copied
from APIGateway's own publisher, the one genuinely-wired reference in this
repo) only handled `datetime`, not `UUID`. Every event dataclass here
carries raw `user_id`/`tenant_id` UUID fields, so the very first
`user.created` publish failed with `Object of type UUID is not JSON
serializable`, silently swallowed by the fire-and-log `except Exception`
— confirmed via container logs, not a crash. Fixed by adding a `UUID` case
to `_default_serializer`. **This is a latent bug in APIGateway's own
`publisher.py` too** (never triggered there because its own event payloads
apparently never carry a raw UUID field directly) — fixed here only, not
backported, since APIGateway's own tests/usage don't exercise it.

**3. Confirmed working end-to-end.** Built the image, ran it against real
Postgres + RabbitMQ on the shared `backend` network, created a user via
HTTP, confirmed it via a separate `GET` request, bound a temporary queue
to `identity.events` and confirmed the exact `user.created` payload
(`user_id`, `tenant_id`, `email`, `display_name`, `status`) arrived —
matching IAM's `UserProjection` fields exactly, so IAM's still-deferred
consumer has a real, correctly-shaped producer waiting for it whenever
that consumer gets built.

Everything else (data model, domain events, services, routers, Alembic
migration — 3 tables, `platform-invitations` prefix) matched the plan as
written.
