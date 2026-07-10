# User — Implementation Notes

## Siloed Multi-tenancy (database-per-tenant) — opt-in

Supports the platform's Siloed multi-tenancy standard, mirroring IAM (the
reference implementation — see `services/IAM/TODO.md`):

- `get_db` (`app/infrastructure/database/dependencies.py`) routes each request
  to its tenant's own database when `siloed_multitenancy_enabled`, failing
  closed (400) if no `X-Tenant-ID` is present. Default OFF → shared-schema
  unchanged.
- `app/infrastructure/database/tenant_routing.py` builds the shared
  `TenantEngineRegistry` (`shared/db/`); `tenant_resolver` selects the dev
  `template` resolver or the production `control_plane` resolver (fetches each
  tenant's DSN from Tenent). Config flags in `app/core/config.py`.
- Per-tenant migrations: `alembic/env.py` accepts a target URL; run
  `scripts/tenant_migrations.py` to apply `upgrade head` across tenant DBs.
- `tenant_id` column + required-kwarg scoping stays as defense-in-depth.
- Verified: 61/61 tests (12 in `tests/unit/test_siloed_multitenancy.py`); ruff
  clean; 0 new mypy errors.

Blocked (not this service's to build): physical `CREATE DATABASE`/drop on
tenant provisioning/offboarding (Tenent + infra), PgBouncer, secrets backend.

**Status: Implemented.** Merges `UserManagement`, `UserLifecycleManagement`,
and `UserProfileManagement` (three services built separately earlier this
session) into one deployable service. 42/42 tests pass, real Postgres
migration applied against the reused `nutratenant_user` database, real
Docker end-to-end verification done. The three source services have been
removed — see "Removal" at the bottom.

## Why merge

The user asked directly: combine the three into one service, verify it
works, then remove the originals. Mirrors a pattern already established in
this repo — `Tenent` merges what were originally three separate services
(TenantManagement/TenantLifecycle/TenantIsolation) into one, with
in-process sync instead of HTTP calls between them.

## What the merge actually changed (not just a file move)

Physically combining three services into one made several things that
existed *purely because of the service boundary* unnecessary:

1. **`UserLifecycleClient`/`UserProfileClient` (HTTP clients) are gone
   entirely.** UserLifecycleManagement used to fail-fast fetch
   UserManagement's user record over HTTP, validate transitions against
   its own local copy of the status, then fire-and-log sync the result
   back over the network — accepting that the two copies could drift if
   that last call failed. UserProfileManagement had the same fail-fast
   existence-check pattern for its own writes. Now there is one `User` row,
   one transaction, one `UserRepository` — `ProfileService`/`AvatarService`
   call `UserRepository.get_by_id` directly; `UserService`'s own transition
   logic never leaves the process. There is no second copy to drift from.

2. **`locked` is a first-class `User.status` value now, not a proxy.**
   UserLifecycleManagement tracked its own richer state machine (including
   `locked`) in a separate `LifecycleState` table, because "locked" had no
   meaning to UserManagement — it just saw `suspended` (the proxy target).
   Merged: `UserStatus` is one enum (`pending/active/suspended/locked/
   deactivated`), `locked_reason`/`locked_by` are plain nullable columns on
   `User` itself. No proxy, no separate table, no drift risk.

3. **One status machine, one audit table.** UserManagement's own
   `UserStatusHistory` and UserLifecycleManagement's `LifecycleEvent` were
   two audit tables for what is now the same set of transitions.  Merged
   into one `UserStatusHistory` with an `action` column (`activate` vs
   `onboard`, `deactivate` vs `offboard`, etc.) carrying the verb
   distinction the old `LifecycleEvent.event_type` used to.

4. **No separate `/api/v1/user-lifecycle` gateway prefix.** That prefix
   only ever existed to keep two different upstream *containers* from
   colliding at the gateway (`/api/v1/users` → UserManagement,
   `/api/v1/user-lifecycle` → UserLifecycleManagement). Same container now
   — `lock`/`unlock`/`onboard`/`offboard`/`unsuspend`/`restore` all live
   directly under `/api/v1/users/{id}/...`, same as `activate`/`suspend`/
   `deactivate` always did. Simpler API surface, one less rename to explain.

5. **Real FKs where there used to be cross-service "projection" columns.**
   `UserProfile.user_id`, `UserPreferences.user_id`, `Avatar.user_id`,
   `ContactInfo.user_id`, and `UserStatusHistory.user_id` are now real
   `ForeignKey("users.id", ondelete="CASCADE")` columns — they were
   deliberately *not* FKs in the three separate services (the
   plain-column-not-FK convention this repo uses whenever a reference
   crosses a service/database boundary), but that reasoning no longer
   applies once everything lives in the same database.

## Two real bugs found only by real Docker verification (not by tests)

The unit test suite (SQLite) didn't catch either of these — both are
specifically the kind of thing that only shows up against a real Postgres
database with real constraints, which is exactly why this repo's
convention is to verify every service against a genuinely running
container before calling it done.

**1. `UserStatusHistory` ordering was not actually reliable.** The
original design ordered by `occurred_at DESC, id DESC` (a UUID tiebreaker).
Two transitions inside one fast test landed on an *identical* `occurred_at`
(SQLite's `now()` is only second-resolution) and the UUID tiebreaker isn't
time-ordered, so "most recent transition first" wasn't actually guaranteed
— caught by a new test (`test_offboard_records_distinct_action`) asserting
on `items[0]`. Fixed: `seq`, a plain auto-incrementing integer, is now the
real primary key (portable across SQLite and Postgres — `BigInteger`
doesn't get SQLite's rowid-autoincrement aliasing, only `Integer` does);
`id` stays as a separate unique UUID for external reference. Ordering and
cursor pagination both use `seq` now, not `(occurred_at, id)`.

**2. The `users.status` CHECK constraint never got updated for `locked`.**
The reused `nutratenant_user` database's `status` column had a CHECK
constraint from the original UserManagement build — `IN
('pending','active','suspended','deactivated')`, no `locked`. The merge
migration added `locked_reason`/`locked_by` *columns* but missed the
constraint entirely (SQLite doesn't enforce `CheckConstraint` bodies the
same way, so 42/42 tests passed while `lock` would have failed outright
against real Postgres with a real `IntegrityError`). Found and fixed via
real Docker verification — a `POST .../lock` failed with
`CheckViolationError` against the live container, not silently.

## Migrating onto the existing `nutratenant_user` database

Reused UserManagement's existing Postgres database rather than starting a
fresh one — it already had real (if sparse) dev/test data (4 users, 5
status-history rows) that a `DROP DATABASE`/`TRUNCATE` would have
destroyed for no real benefit. Two migration wrinkles worth recording:

- The `alembic_version` bookkeeping table pointed at UserManagement's old
  revision ID, which doesn't exist in this service's fresh migration
  history — blocked Alembic entirely (including read-only operations).
  Fixed by clearing that one row directly (confirmed with the user first —
  this is purely Alembic's own internal tracking, not business data).
- Adding `user_status_history.action` as non-nullable against a table with
  existing rows needed the standard add-with-backfill-then-drop-default
  pattern (backfilled using each row's own `to_status` as a reasonable
  stand-in for the unknown historical verb).

## Verification

1. `uv sync`, `uv run pytest -v` — 42/42 passing, covering CRUD, every
   status transition (activate/onboard/suspend/unsuspend/lock/unlock/
   deactivate/offboard/restore), invitations, and profile/preferences/
   avatar/contacts — all previously three separate test suites, now one,
   with the fake-HTTP-client fixtures gone (nothing to fake anymore).
2. `alembic upgrade head` against real Postgres — 7 tables, all existing
   data preserved.
3. `ruff`/mypy clean, same accepted 10-error baseline shape as every
   sibling service.
4. Real Docker end-to-end: created a user, activated, locked (in-process,
   confirmed the CHECK constraint bug above), unlocked, wrote a profile,
   deleted + restored, and confirmed the full status-history audit trail
   (`restore → unlock → lock → activate`, correctly ordered by `seq`).
   Confirmed the RabbitMQ publish path independently by binding a
   temporary queue to `identity.events` and observing a real
   `user.created` message land on it.
5. APIGateway: 126/126 tests passing after collapsing
   `UpstreamService.USER_MANAGEMENT`/`USER_LIFECYCLE_MANAGEMENT`/
   `USER_PROFILE_MANAGEMENT` into one `USER` value (route count 24 → 23,
   unique upstreams 8 → 6 — the `/api/v1/user-lifecycle` route was removed
   outright, not renamed, since the prefix no longer serves any purpose).

## Removal

`services/UserManagement`, `services/UserLifecycleManagement`, and
`services/UserProfileManagement` have been removed (`git rm -r`) — their
functionality is fully covered here, all wiring (docker-compose.yml,
APIGateway) repointed first and verified green before removal. Their
Postgres databases (`nutratenant_user_lifecycle`, `nutratenant_user_profile`)
were left in place rather than dropped (destructive database operations
require explicit confirmation per this session's established practice) —
they're empty of anything but already-truncated test data and can be
dropped manually if desired.
