# IAM — Siloed Multi-tenancy Migration Standard

**Status: IN PROGRESS — IAM-side implemented (opt-in); cross-service pieces
still blocked.** IAM shipped shared-schema (one `nutratenant_identity`
database, `tenant_id` column + required kwarg). This pass adds a working,
opt-in **database-per-tenant** path: a shared connection router, a
tenant-aware fail-closed `get_db`, per-tenant Alembic migrations, and an
orchestrator — all defaulting OFF so the shared-schema deployment is
unchanged. What remains is genuinely **not IAM's to build** (the Tenent-owned
Control Plane, the gateway's subdomain resolver, PgBouncer) — see
"Dependencies" and the unchecked boxes below.

## Implemented in this pass

- **Shared connection router** (`shared/db/`): `TenantConnectionResolver` +
  `TemplateConnectionResolver` (resolver.py), `TenantEngineRegistry` with
  per-tenant engine caching + bounded eviction (registry.py), fail-closed
  `tenant_context` (tenant_context.py). Built in `shared/` so User/Org/Auth
  reuse it verbatim.
- **IAM routing**: `app/infrastructure/database/tenant_routing.py` builds the
  registry from settings; `get_db` (dependencies.py) routes to the request
  tenant's database when `siloed_multitenancy_enabled`, else the shared DB —
  no behaviour change when off. Config flags in `app/core/config.py`.
- **Resolver selection** (`tenant_resolver`): `template` for dev, or
  `control_plane` — now that Tenent's Control Plane exists, IAM fetches each
  tenant's DSN from it via `shared/db/ControlPlaneConnectionResolver`
  (`control_plane_base_url`). No credentials in IAM config in that mode.
- **Per-tenant migrations**: `alembic/env.py` takes a target URL
  (`-x db_url=` / `ALEMBIC_TARGET_URL`); `scripts/tenant_migrations.py`
  iterates tenants and applies `upgrade head` to each, resumable + idempotent.
- **Verified**: 76/76 tests green (12 in `tests/unit/test_siloed_multitenancy.py`
  covering both resolvers, registry isolation, eviction, fail-closed context,
  and `get_db` routing); ruff clean; 0 new mypy errors; the orchestrator
  end-to-end migrates two separate SQLite tenant DBs (14 tables each) and is
  idempotent on re-run.

> The two pillars remain the north-star (database-per-tenant + subdomain
> routing — see root `README.md` → "Core Architectural Pillars (Target)").
> Default stays shared-schema until the blocking dependencies below exist.

## What "Siloed" means for IAM

Each tenant gets its own **physical IAM database**, resolved per request. The
`tenant_id` column stops being the *isolation mechanism* and becomes
*defense-in-depth* — isolation moves up to the connection itself: a request
for tenant A can only ever open a session against tenant A's database.

This is a bigger change to IAM's **infrastructure layer** than to its domain
logic — the roles/permissions/ABAC engine is largely untouched; what changes
is *which database the session points at* and *how migrations reach N
databases instead of one*.

## Current state (what has to change)

| Area | Today | File(s) |
|---|---|---|
| Engine | One module-level engine bound to `settings.database_url` | `app/infrastructure/database/engine.py` |
| Session | One `SessionLocal` factory bound to that engine | `app/infrastructure/database/session.py` |
| Request DB | `get_db()` yields from the single `SessionLocal` — tenant-blind | `app/infrastructure/database/dependencies.py` |
| Migrations | Alembic runs against the single `settings.database_url` | `alembic/env.py` (offline L22, online L40) |
| Isolation | `tenant_id` required kwarg on every repo query | `app/repositories/*.py` (e.g. `role.py`) |
| Models | Every model carries a `tenant_id` column | all 10 under `app/models/` |
| Config | Single `database_url` | `app/core/config.py` |

## Required changes

### 1. Tenant-aware connection routing (the core change)
- [x] **Per-tenant engine registry** — `shared/db/registry.py`
      (`TenantEngineRegistry`): resolves tenant → connection string → cached
      `AsyncEngine` + `async_sessionmaker`.
- [x] **Fail-closed `get_db()`** — `app/infrastructure/database/dependencies.py`
      routes to the request tenant's engine (from `X-Tenant-ID`) when
      `siloed_multitenancy_enabled`; a missing tenant 400s with no shared
      fallback. Off by default → shared-schema unchanged.
- [x] **Built in `shared/`** — `shared/db/` (resolver + registry + context),
      consumed by IAM via `app/infrastructure/database/tenant_routing.py`.
      User/Org/Auth reuse it verbatim.
- [x] Engine cache is **bounded** (`max_engines` → LRU eviction + dispose).
      / ⛔ Routing every tenant connection through **PgBouncer** is
      deployment config (docker-compose/k8s) — not IAM code.

### 2. Control Plane dependency
- [x] Consume a **connection registry** via the `TenantConnectionResolver`
      seam. Two resolvers now ship, selected by `tenant_resolver`:
      `TemplateConnectionResolver` (dev) and — now that Tenent exposes the
      Control Plane — `ControlPlaneConnectionResolver` (`tenant_resolver=
      control_plane` + `control_plane_base_url`), which fetches each tenant's
      DSN from Tenent. Per-tenant engine caching already means the resolver is
      hit once per tenant (a short-TTL re-resolution cache is a later
      refinement, only needed if a live tenant's database moves).
- [x] IAM config holds **no raw per-tenant credentials** — with the Control
      Plane resolver the credential never touches IAM config at all: Tenent
      assembles the DSN from its own `SecretsProvider`. (Template mode still
      builds URLs from a template/overrides/env for dev.)

### 3. Migrations: one → N databases
- [x] `alembic/env.py` takes a **target URL** (`-x db_url=` /
      `ALEMBIC_TARGET_URL`) instead of only `settings.database_url`.
- [x] **Migration orchestrator** — `scripts/tenant_migrations.py` iterates
      tenants and applies `upgrade head` to each, with per-tenant
      success/failure reporting. (Tenant list is passed in / env for now; the
      Control Plane will own it once available.)
- [x] Partial failure is handled: per-tenant try/continue, and re-running is
      **idempotent** (verified end-to-end on two SQLite tenant DBs).

### 4. Tenant provisioning / de-provisioning hooks
- [x] Creating + migrating a tenant's IAM schema is implemented
      (`tenant_migrations.py` / `get_tenant_engine`). ⛔ Wiring it to fire
      from Tenent's `provisioning` state (and physical `CREATE DATABASE`)
      belongs to Tenent.
- [ ] On tenant offboarding/deletion, drop/archive IAM's tenant DB as a unit
      — not yet wired.

### 5. Domain layer (mostly unchanged — keep as defense-in-depth)
- [x] `tenant_id` column + required-`tenant_id`-kwarg repository discipline
      **kept unchanged** — still the backstop, lets both models coexist.
- [ ] Formal audit that no query can span tenants (structurally impossible
      once the session is tenant-bound, but the review is still worth doing).

### 6. Tests
- [x] `tests/unit/test_siloed_multitenancy.py` — two tenants resolve to two
      distinct engines and tenant A's write is invisible to tenant B's
      session using a raw probe table (no `tenant_id` guard), proving
      isolation moved to the connection. Plus resolver, eviction, fail-closed
      context, and `get_db` routing.
- [x] Existing suite green — 75/75 (64 prior + 11 new), no domain regression.

## Design decisions / guardrails

1. **Isolation moves to the connection; `tenant_id` stays as a backstop.**
   The security property becomes "you physically cannot open the wrong
   database," with the column as a second layer, not the primary one.
2. **Fail closed on unresolved tenant.** No default/shared database
   fallback — an unroutable request is a 400/401, never a silent read from
   the wrong place.
3. **IAM consumes, Tenent owns.** The Control Plane registry and per-tenant
   provisioning are Tenent's responsibility; IAM must not duplicate that
   mapping.
4. **The router is shared infrastructure.** Implement in `shared/` so
   IAM/User/Organization/Authentication share one audited implementation.

## Dependencies (blocking — not IAM's to build)

- **Control Plane DB** + subdomain→connection registry — owned by **Tenent**.
- **Tenant Resolver middleware** (subdomain → tenant) — owned by
  **APIGateway**.
- **PgBouncer** in `docker-compose.yml` / k8s — infrastructure.
- **Shared connection router** in `shared/` — cross-service, prototype first.
      ✅ Done (`shared/db/`); the remaining three are the true blockers.

## Definition of done

- [x] A request carrying tenant A's context opens a session against tenant
      A's physical database; tenant B is unreachable from that request.
      *(Proven by `test_siloed_multitenancy.py` + `get_db` routing.)*
- [x] `alembic upgrade head` applies to every tenant DB via the orchestrator,
      idempotently and resumably. *(Verified end-to-end on two tenant DBs.)*
- [ ] New-tenant provisioning creates + migrates an IAM database before the
      tenant is `active`; offboarding drops it cleanly. *(Migrate step done;
      firing from Tenent's lifecycle + offboarding drop still pending.)*
- [x] Existing IAM test suite green, plus new per-tenant isolation tests.
      *(75/75.)*
- [x] No IAM code holds raw per-tenant DB credentials or a hard-coded
      `database_url` for tenant data. *(Resolver builds URLs from
      template/overrides/env.)*

## How to turn it on

```bash
# .env (or environment)
SILOED_MULTITENANCY_ENABLED=true
TENANT_DATABASE_URL_TEMPLATE=postgresql+asyncpg://user:pass@pgbouncer:6432/iam_{tenant}
# optional: pin specific tenants elsewhere
# TENANT_DATABASE_OVERRIDES={"<tenant-uuid>": "postgresql+asyncpg://.../iam_special"}

# migrate every tenant database
uv run python -m scripts.tenant_migrations upgrade <tenant-id> [<tenant-id> ...]
```
