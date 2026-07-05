# UserProfileManagement — Implementation Plan

**Status: Implemented.** Built per the plan below — 17/17 tests passing,
real Postgres migration applied, real Docker end-to-end verification done
against a genuinely running UserManagement container (see "Second pass:
what was actually built" at the bottom). Not listed in
`Implementation-order.md`'s numbered sequence (it's a supplementary
service, not on the core priority path); no ordering constraint to satisfy
before starting it.

## Scope note resolved before writing this plan

`README.md`'s example JSON shows `first_name`/`last_name` alongside
`timezone`/`language`:
```json
{ "first_name": "Nazmul", "last_name": "Diptu", "timezone": "Asia/Dhaka", "language": "en" }
```
But `UserManagement` (built earlier this session) already owns
`first_name`/`last_name` on its own `User` model — used to compute
`display_name`, which IAM's `UserProjection` and the `identity.events`
RabbitMQ exchange both depend on. Re-declaring `first_name`/`last_name`
here would create a second, divergence-prone source of truth for the same
two fields (unlike the `LOCKED`/proxy-status case in
UserLifecycleManagement, this isn't a state machine sitting on top of an
existing record — it'd just be plain duplicated columns with no
reconciliation mechanism).

This is a smaller, more contained overlap than the previous two conflicts
this session (a couple of fields, not a whole CRUD/lifecycle surface), so
resolving it directly here rather than pausing to ask: **this service does
not store `first_name`/`last_name`.** The README's example JSON is read as
an illustrative *merged view* (what a client sees after combining
UserManagement's name with this service's own preferences), not a literal
schema. `user_profiles` here holds `bio`/`pronouns`/`display_name_override`
instead — profile-card content UserManagement was never meant to own — and
`user_preferences` holds `locale`/`timezone` (matching the README's own
"Locale settings"/"Timezone settings" as separate Responsibilities bullets,
distinct from generic "Preferences"). Every literal endpoint and "Owns"
table in the README is still implemented; only the *column* shape of
`user_profiles` deviates from the example JSON, and only for the two
fields that already exist elsewhere.

**No blob storage exists anywhere in this repo** — no dedicated File
Storage service, no S3/CDN abstraction in `shared/`. `avatars` therefore
stores a URL reference the client already uploaded elsewhere (e.g. to a
CDN), not raw image bytes — consistent with this repo's demonstrated
restraint about not inventing infrastructure a request doesn't actually
need yet.

## Architectural conventions to reuse

- Repository/service/DI pattern, `PageResult`/cursor pagination (not
  actually needed here — every resource in this service is a 1-row-per-user
  singleton, no list endpoints — but `repositories/base.py` copied anyway
  for `BaseRepository`'s session-holding convention, consistency with every
  other service in this repo).
- **Fail-fast HTTP client to UserManagement**, shaped exactly like
  `OrganizationManagement/app/infrastructure/clients/tenent_client.py` and
  `UserLifecycleManagement/app/infrastructure/clients/user_lifecycle_client.py`'s
  `get_user`: `UserProfileClient.assert_user_exists(user_id, tenant_id)`,
  called once, the first time any row is created for a given `user_id` —
  not on every read (that'd be a wasteful live check on every `GET`).
  Subsequent operations against an already-known `user_id` skip the check
  entirely, matching UserLifecycleManagement's own "bootstrap once, trust
  local state after" pattern.
- Domain layer: `enums.py` (none needed — no status/state machine in this
  service), `exceptions.py`, `commands.py`, no `events.py` — no audit
  trail or RabbitMQ publishing for the same reason OrganizationManagement
  and UserLifecycleManagement both skip it: no consumer exists for
  profile-change events, and nothing here is a state transition worth
  auditing (unlike lifecycle status changes). Profile edits are simple
  overwrite updates, no history retained — no evidence any of the four
  "Owns" tables need historical snapshots (unlike OrganizationManagement's
  settings, which explicitly needed a version history).

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `user_profiles` | user_id (plain, PK), tenant_id, bio (nullable), pronouns (nullable), display_name_override (nullable), created_at, updated_at | One row per user, created lazily on first `PATCH /profiles/{id}`. |
| `user_preferences` | user_id (plain, PK), tenant_id, locale (default "en"), timezone (default "UTC"), extra (JSON, dialect-generic, for anything beyond locale/timezone), created_at, updated_at | Same lazy-creation pattern. |
| `avatars` | user_id (plain, PK), tenant_id, url, content_type (nullable), uploaded_at | `POST` upserts, `DELETE` removes the row entirely (not a soft-delete — no history value in a removed avatar reference). |
| `contact_info` | user_id (plain, PK), tenant_id, phone (nullable), secondary_email (nullable), address (JSON, nullable — street/city/postal/country as sub-fields, dialect-generic), created_at, updated_at | Same lazy-creation pattern. |

All four `user_id` columns are plain UUID, never FKs — UserManagement owns
the real row in a different service/database, same convention every
service this session has followed.

## Services

- `profile_service.py` — `ProfileService`: `get_profile`/`update_profile`
  (upsert — creates on first call, fail-fast validates the user exists via
  `UserProfileClient` only on that first create), `get_preferences`/
  `update_preferences`, `get_contacts`/`update_contacts` — same
  get-or-create-then-upsert shape repeated three times for three tables;
  not factored into one generic helper since each table's fields differ
  enough that a shared abstraction would need as much special-casing as
  three plain methods.
- `avatar_service.py` — `AvatarService`: `set_avatar(user_id, tenant_id, url, content_type)`
  (upsert, fail-fast validates user existence only if no local row exists
  yet for this `user_id` across *any* of the four tables — reuses
  `ProfileService`'s own existence-check bootstrap rather than re-checking
  independently), `delete_avatar`, `get_avatar`.

## Schemas

`schemas/profile.py`, `preferences.py`, `avatar.py`, `contact.py` —
straightforward request/response pairs per resource, `AppBaseModel` base
copied verbatim from every other service this session.

## Routers (`api/v1/profiles_router.py`, mounted at `/api/v1/profiles/{user_id}`)

No gateway collision to resolve this time — `/api/v1/profiles` is a
literal prefix nothing else in this repo has claimed (checked
`route_service.py`'s registry).

- `GET/PATCH .../` (bare `/api/v1/profiles/{user_id}`)
- `POST/DELETE .../avatar`
- `GET/PATCH .../preferences`
- `GET/PATCH .../contacts`

All `X-Tenant-ID` scoped. 404 if UserManagement doesn't have this user (on
first write only, per the fail-fast-once pattern above); reads for a
`user_id` with no local row yet return an empty/default-valued response
rather than 404 (a user who exists in UserManagement but has never touched
their profile isn't an error — same reasoning IAM's own `UserProjection`
lookups already apply: absence isn't failure).

## Wiring (once implemented)

- `docker-compose.yml`: new `user-profile-management` service, port
  **8025** (next unused after UserLifecycleManagement's 8024). Needs
  Postgres + `USER_MANAGEMENT_BASE_URL` pointing at UserManagement's
  container — no RabbitMQ (no publish, per Domain events above).
- `infrastructure/postgres/init.sql`: add `nutratenant_user_profile`.
- APIGateway: new `UpstreamService.USER_PROFILE_MANAGEMENT` +
  `user_profile_management_base_url`, route registry entry for
  `/api/v1/profiles`.

## Verification (once implemented)

1. `uv sync`, `uv run pytest -v` — full suite green, including: reading a
   profile for a user who has one row created vs. one who has none yet
   (default-valued response, not 404); updating preferences/contacts
   independently doesn't touch the other tables; avatar delete actually
   removes the row (`get_avatar` after `delete_avatar` returns empty, not
   a stale cached URL).
2. `alembic revision --autogenerate` against real local Postgres, `upgrade
   head` — confirms all 4 tables.
3. `ruff`/mypy clean, same accepted-gap shape as every sibling service.
4. Real Docker end-to-end: boot this service **and** UserManagement
   together, create a real user via UserManagement, `PATCH` a profile/
   preferences/contact/avatar against this service, confirm each persists
   via a separate `GET` — and confirm a `PATCH` against a `user_id`
   UserManagement doesn't have actually 404s (the fail-fast client's
   existence check genuinely firing, not silently accepted).

## Second pass: what was actually built

Followed the plan above almost exactly. One deliberate simplification from
the original design, no real bugs found this time (the first build this
session where the 17 tests passed clean on the first run and the Docker
verification also passed clean on the first try):

**Existence-check bootstrap simplified.** The plan called for
`AvatarService` to "reuse `ProfileService`'s own existence-check bootstrap
rather than re-checking independently" — i.e. check across all four tables
for any existing row before deciding whether to call UserManagement.
Implemented instead: each of the four resources (profile, preferences,
contacts, avatar) independently checks only its own table and calls the
fail-fast client only if *that* table has no row yet for the user_id. A
user's first-ever write to a second resource type (e.g. profile already
exists, now writing preferences for the first time) triggers one extra
existence check it technically didn't need — correctness is identical
either way, this only costs one avoidable HTTP call in a fairly rare path,
and the simpler per-resource version avoids a cross-table existence-guard
component the plan hadn't actually detailed the shape of. Not backporting
the cross-table check unless the extra HTTP call turns out to matter in
practice.

**Confirmed working end-to-end against a real running UserManagement
container.** Built both images, ran them on the shared `backend` network,
created a real user via UserManagement, then `PATCH`ed profile,
preferences, and contacts and `POST`ed an avatar against this service —
each confirmed via a separate `GET`, not just trusting the write response.
Separately confirmed the fail-fast existence check actually rejects: a
`PATCH` against a `user_id` UserManagement has never heard of returned a
real `404`, not a silently-accepted write.

Everything else (data model — deliberately not storing first_name/
last_name, `user_preferences`/`avatars`/`contact_info` shapes, the
lazy-create-on-first-write pattern, `/api/v1/profiles` routing with no
collision to resolve) matched the plan as written.
