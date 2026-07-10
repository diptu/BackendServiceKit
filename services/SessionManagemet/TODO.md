# SessionManagement — Implementation Notes

**Status: Implemented, siloed from day one.** A new service built directly
against the platform's Siloed multi-tenancy standard (IAM is the reference
implementation — `services/IAM/TODO.md`). 25/25 tests pass, `scripts/lint.sh`
(ruff + format + mypy + pytest + bandit) is fully green, and both the shared
and per-tenant migration paths are verified against SQLite.

## What it owns

Higher-level authenticated **session/device tracking** — concurrent sessions,
"where am I logged in", force-logout — distinct from Authentication's own
refresh-token rotation (which stays where it is). Endpoints match the README
design doc:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/sessions` | Create a session → returns the raw session token once |
| GET | `/api/v1/sessions` | List (tenant-scoped; `?user_id=`, `?active_only=`) |
| GET | `/api/v1/sessions/me` | Resolve the caller's own session from `X-Session-Token` |
| POST | `/api/v1/sessions/revoke-all` | Revoke all of a user's sessions |
| GET | `/api/v1/sessions/{id}` | Get one |
| DELETE | `/api/v1/sessions/{id}` | Revoke one (idempotent, 204) |
| POST | `/api/v1/sessions/{id}/refresh` | Extend an active session |
| GET | `/api/v1/users/{user_id}/sessions` | A user's sessions |
| DELETE | `/api/v1/users/{user_id}/sessions` | Revoke a user's sessions |

## Design decisions

1. **Siloed multi-tenancy is opt-in and built in.** `get_db` routes each
   request to its tenant's own database when `siloed_multitenancy_enabled`
   (fail-closed 400 without `X-Tenant-ID`), else the single shared-schema DB —
   via the shared `shared/db/` router. `tenant_resolver` selects the dev
   `template` resolver or the production `control_plane` resolver (fetches the
   DSN from Tenent). `tenant_id` is a required repository kwarg — the isolation
   backstop in siloed mode, the primary mechanism in shared-schema mode.
2. **Only a SHA-256 hash of the session token is stored.** The raw
   `secrets.token_urlsafe` token is returned once at creation and is what
   `/sessions/me` and refresh look up by — the same pattern Authentication uses
   for refresh tokens.
3. **`user_id` is a projection reference** (plain column, not an FK) — the User
   service owns the identity.
4. **Status is derived, not stored** — `active`/`expired`/`revoked` computed
   from `revoked_at`/`expires_at` at read time.
5. **Revoke is idempotent** — revoking an unknown/already-revoked session is a
   204 no-op, not a 404 that would leak whether it exists; cross-tenant lookups
   404 (never reveal another tenant's session).

## Verification

- `uv run pytest` — 25/25: create (token + active session), get, list +
  `active_only` filter, `/sessions/me` (valid + generic-401 on bad token),
  refresh extends expiry, idempotent revoke → status `revoked`, revoke-all,
  user-scoped list/delete, cross-tenant isolation, tenant-header-required; plus
  the 12-test `test_siloed_multitenancy.py` (resolver, registry isolation,
  eviction, fail-closed context, `get_db` routing, control-plane resolver).
- `scripts/lint.sh` clean: ruff, `ruff format --check`, `mypy --strict`
  (0 errors), pytest, bandit (0 issues).
- Migrations verified: `alembic upgrade head` (shared) and
  `scripts/tenant_migrations.py` (two isolated per-tenant SQLite DBs, each with
  `sessions` + `alembic_version`).
- Added to `cd.yml`'s build matrix (CD is not auto-discovered).

## Not done (follow-up)

- Real Postgres + Docker end-to-end verification (SQLite only so far).
- Wire into `docker-compose.yml` and APIGateway's route registry
  (`/api/v1/sessions` → this service) — pick a port (suggest 8025).
- Physical `CREATE DATABASE`/drop on tenant provisioning/offboarding (Tenent +
  infra), PgBouncer, secrets backend — the platform-wide siloing blockers.
- OpenTelemetry tracing wiring (kept lean for now; deps omitted).
- Emit `session.created` / `session.revoked` events for downstream consumers.
