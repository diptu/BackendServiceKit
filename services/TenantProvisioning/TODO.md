# TenantProvisioning — Implementation Notes

**Status: Implemented.** The physical side of Siloed multi-tenancy: it creates
a tenant's own database, migrates every managed service's schema into it, and
registers the connection in the Tenent Control Plane. 8/8 tests pass,
`scripts/lint.sh` (ruff + format + mypy + pytest + bandit) is fully green, and
the workflow is exercised end-to-end against real SQLite tenant databases.

## Key design decision: global orchestrator, NOT siloed

Like the Control Plane it works alongside, this service is deliberately **not**
database-per-tenant — its `provisioning_jobs` table spans all tenants (it is
the thing that *creates* per-tenant databases). Its `get_db` is a plain
single-database dependency, no `X-Tenant-ID` routing.

## Workflow (`ProvisioningService`)

`provision(tenant_id, subdomain, region)` runs, recording each step on the job:

1. **create_database** — `DatabaseProvisioner.create` (Postgres `CREATE
   DATABASE` in prod; a per-tenant SQLite file locally/in tests)
2. **run_migrations** — `MigrationRunner.migrate` applies every managed
   service's schema into the new database
3. **register_control_plane** — `ControlPlaneRegistrar` POSTs the connection to
   Tenent (`/api/v1/control-plane/connections/{id}`)
4. **done** → `completed`

Idempotent (a `completed` tenant is not re-provisioned), retryable (`/retry`
re-runs a `failed` job), and reversible (`DELETE` deprovisions: Control Plane
disable + drop database). A failure records `status=failed` + the failing step
+ error on the job rather than throwing.

## Seams (injectable, so it's testable without live infra)

- **`DatabaseProvisioner`** — `LocalDatabaseProvisioner` (SQLite files, dev/test)
  / `PostgresDatabaseProvisioner` (real `CREATE/DROP DATABASE` via an admin
  connection, `AUTOCOMMIT`). Selected by `provisioner_backend`.
- **`MigrationRunner`** — `MarkerMigrationRunner` (default) records the migrated
  services into the tenant DB, giving a real observable effect. A production
  `SubprocessMigrationRunner` would shell out to each service's
  `scripts/tenant_migrations.py` against the new DSN.
- **`ControlPlaneRegistrar`** — `HttpxControlPlaneRegistrar` (Tenent) /
  `NullControlPlaneRegistrar` (dev/test or when registration is disabled).

## API

`POST /api/v1/provisioning/tenants` (start), `GET` (list, `?status=`),
`GET /{tenant_id}` (status), `POST /{tenant_id}/retry`, `DELETE /{tenant_id}`
(deprovision). Internal-only — driven by Tenent's lifecycle, not the gateway.

## Verification

- `uv run pytest` — 8/8: full workflow (creates + migrates a real tenant DB,
  marker table asserts every managed service was migrated), idempotency, get,
  list, 404, deprovision (drops the tenant DB), retry-on-completed no-op, and
  failure recorded on the job.
- `scripts/lint.sh` clean (ruff, format, `mypy --strict` 0 errors, pytest,
  bandit 0 issues); `alembic upgrade head` verified against SQLite.
- Added to `cd.yml`'s build matrix.

## Not done (follow-up)

- Real Postgres verification of `PostgresDatabaseProvisioner` (`CREATE DATABASE`)
  and a real `SubprocessMigrationRunner` running each service's migrations.
- Run the workflow on a background worker (Celery/RQ) instead of inline; the
  API would enqueue and return `202`.
- Wire Tenent's `provisioning` lifecycle state to call this service (today
  Tenent's `control_plane_auto_register` registers a placeholder; this service
  is the piece that does the physical work).
- A real secrets backend so `secret_ref` resolves to per-tenant DB credentials.
- Suggested port: 8003. Wire into `docker-compose.yml`.
