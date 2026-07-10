# 0007. Onboarding/Offboarding/Migration become one new service; Configuration/Compliance extend Tenent

Date: 2026-07-06
Status: Accepted

## Context

Five services were planned (#146-150 in the original 150-service roadmap):
Tenant Onboarding Automation, Offboarding, Migration, Configuration, and
Compliance. None exist yet. A Principal Engineer review was asked to
determine final boundaries against the existing `Tenent` service (which
already merges Tenant Management + Lifecycle + Isolation — ADR 0001).

## Decision

Split five candidates into two buckets, not five services and not one:

- **Configuration (#149) and Compliance (#150 — attestation data only, not
  the rules engine) extend `Tenent`** as new sub-resources, the same way
  `TenantSettings`/`TenantMetadata` already work. They're tenant
  *attributes* with the same lifecycle, database, and deployment cadence
  as everything else `Tenent` owns.
- **Onboarding Automation (#146), Offboarding (#147), and Migration (#148)
  become one new service, `TenantOrchestration`.** They're sagas, not
  aggregate data: multi-step, multi-service workflows with a
  background-worker lifecycle and a security profile (irreversible,
  cross-service, compliance-sensitive) that doesn't belong in the same
  blast radius as routine tenant CRUD.

Full evaluation: `docs/architecture/tenant-lifecycle-services.md`.

## Consequences

- Resolves an existing regression for free: `Tenent`'s
  `TenantProvisioningClient` fires events at a deleted service
  (`TenantProvisioning`) — `TenantOrchestration`'s onboarding saga consumes
  those events instead of resurrecting a sixth service.
- Surfaces a real, already-flagged risk and gives it a concrete trigger to
  fix: `Authentication`'s `POST /auth/credentials` has no auth gate (ADR
  0004) because nothing legitimately calls it yet.
  `TenantOrchestration`'s onboarding saga is the first real caller —
  service-to-service trust (mTLS or signed tokens) should land before or
  alongside this service, not after.
- `TenantOrchestration` has a wide dependency fan-out (Tenent, User,
  Authentication, every service holding tenant data for offboarding's
  purge). This is accepted as the correct trade-off, not hidden — the
  alternative (each service exposing an ad hoc delete-everything endpoint
  that `Tenent` calls directly) moves the same fan-out into `Tenent`
  instead, which is worse: it inverts `Tenent`'s current position near the
  root of the dependency graph into one that depends on almost everything.
- `MigrationService` (inside `TenantOrchestration`) is flagged as the most
  likely future split candidate if a dedicated ops/infra team ever forms —
  not split preemptively.
