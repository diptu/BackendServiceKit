# Principal Engineer Review: Tenant Onboarding / Offboarding / Migration / Configuration / Compliance

Date: 2026-07-06
Scope: Evaluate planned services #146-150 against the existing `Tenent`
service and recommend final boundaries.

## Executive Summary

Five candidate services collapse into **one aggregate extension + one new
service**, not five, not one:

1. **#149 (Tenant Configuration) and #150 (Tenant Compliance)** are Tenant
   *attributes* — same shape as the `TenantSettings`/`TenantMetadata`
   sub-resources `Tenent` already owns. Extend `Tenent`. Standing these up
   as separate services would be exactly the nano-service anti-pattern
   this review is meant to avoid: CRUD on a handful of columns, no
   independent scaling or ownership need, same lifecycle as everything
   else in `Tenent`.

2. **#146 (Onboarding Automation), #147 (Offboarding), and #148
   (Migration)** are a different *kind* of thing entirely: multi-service
   **sagas**, not aggregate data. They share a lifecycle (bursty,
   long-running, background-worker-driven), a dependency direction
   (calling outward into Tenent/User/Authentication/Notification — the
   inverse of Tenent's role as a service other things depend *on*), and a
   security profile (irreversible, cross-service, compliance-sensitive
   operations that deserve a narrower blast radius than routine tenant
   CRUD). Recommend one new service: **`TenantOrchestration`**.

3. **This also resolves an existing, already-flagged regression.**
   `Tenent`'s own `TenantProvisioningClient` fires
   `TenantProvisioningStarted`/`Completed`/`Failed` events at a service
   (`TenantProvisioning`) that no longer exists — a dangling reference this
   repo's last audit found and explicitly deferred to "Phase 5, do this
   first" in `Implementation-order.md`. `TenantOrchestration`'s onboarding
   saga is the natural, already-half-wired home for that logic — it should
   *subscribe* to those existing events rather than `Tenent` needing any
   changes, and there is no reason to resurrect `TenantProvisioning` as a
   sixth service.

---

## Recommendation A: Extend `Tenent` (no new service)

### Why #149/#150 belong here, not split out

| Criterion | Assessment |
|---|---|
| Shared business capability | Both are attributes *of* a tenant, same as the settings/metadata `Tenent` already owns |
| Shared data ownership | Same aggregate root (`Tenant.id`), same database |
| Shared lifecycle | Read/written on the same request-response cadence as everything else in `Tenent` — no async/background component |
| Shared deployment | Same container, same deploy cadence — no independent scaling driver |
| Disadvantage of merging | None significant — this is what `Tenent` already does for `TenantSettings`/`TenantMetadata` |
| Disadvantage of splitting out | Nano-service: a handful of columns behind their own API, docker image, CI pipeline, on-call surface, for capability with no independent scaling or ownership justification |

**#150 needs one boundary clarification, not a service boundary:** "Tenant
Compliance" as *per-tenant attestation/status data* (data residency flag,
certification expiry, compliance tier) belongs in `Tenent`. The *rules
engine* that decides what counts as compliant is a different concern —
that's Compliance Management (#85, `Implementation-order.md` Phase 6) and
should read `Tenent`'s attestation data, not own it.

### Recommended Microservice Name
`Tenent` (existing — extended, not renamed)

### Responsibilities (additive)
- Existing: tenant CRUD, lifecycle state machine, cross-tenant isolation
  policy/resource claims (unchanged)
- New: richer per-feature tenant configuration (beyond the current
  timezone/locale/currency `TenantSettings`); per-tenant compliance
  attestation state (data residency, certification status/expiry)

### Internal Modules
- `TenantService`, `TenantLifecycleService`, `IsolationService` (existing)
- New: `TenantConfigurationService` (feature-flag-shaped config, not to be
  confused with platform-wide Feature Flag Service, #45 — this is
  per-tenant override data only)
- New: `TenantComplianceService` (attestation CRUD only — no evaluation
  logic)

### Public APIs (additive)
- `GET/PATCH /api/v1/tenants/{id}/configuration`
- `GET/PATCH /api/v1/tenants/{id}/compliance`

### Domain Model (additive)
- `TenantConfiguration` — `tenant_id` (PK), arbitrary JSON feature-config
  blob or typed columns depending on how many concrete settings exist by
  the time this is built, `updated_at`
- `TenantComplianceStatus` — `tenant_id` (PK), `data_residency_region`,
  `compliance_tier`, `certifications` (JSON list), `attested_at`

### Database Ownership
`Tenent`'s existing Postgres database — two new tables, same schema
namespace, same migration history.

### Events Published
- `tenant.configuration.updated`, `tenant.compliance_status.updated` — for
  a future Compliance Management service (#85) to consume, not build yet

### Events Consumed
None new.

### Dependencies
None new — same as `Tenent` today.

### Future Split Candidates
None identified. Revisit only if per-tenant configuration grows into a
genuinely large, independently-scaled feature-flagging system — at that
point it's arguably absorbed into Feature Management (#44)/Feature Flag
(#45) instead of staying tenant-specific.

---

## Recommendation B: New service — `TenantOrchestration`

### Why #146/#147/#148 belong together, and why they don't belong in `Tenent`

| Criterion | Assessment |
|---|---|
| Shared business capability | All three are **sagas**: multi-step, multi-service workflows triggered by a tenant entering, leaving, or moving within the platform — not CRUD on tenant data |
| Shared data ownership | None of the three primarily *own* tenant attributes — they own workflow/job state (`onboarding_sessions`, `offboarding_requests`, `migration_jobs`) and orchestrate writes to data other services own |
| Shared lifecycle | Bursty and long-running (an onboarding saga runs once per signup over seconds-to-minutes; an offboarding retention countdown runs over days-to-months; a migration job runs over hours) — none matches `Tenent`'s synchronous request-response lifecycle |
| Shared deployment characteristics | All three need background-worker execution (Celery, matching the pattern APIGateway's worker queues and the former `TenantProvisioning`'s worker already established) — not just a FastAPI request handler |
| Shared security considerations | All three perform **irreversible or cross-service-fanning-out operations** (creating a paying customer's initial access, permanently destroying a tenant's data platform-wide, moving a tenant's data across infrastructure). Bundling that with routine tenant CRUD in `Tenent` widens the blast radius of `Tenent`'s everyday code changes into destructive territory it doesn't need today |
| Disadvantage of merging into `Tenent` | Inverts `Tenent`'s place in the dependency graph. Today, `Tenent` is close to the dependency root — other services call it, it calls almost nothing. Onboarding/Offboarding/Migration need to call *outward* into User (create the owner's identity), Authentication (set the owner's initial credential — see the note below), and eventually Notification. Putting that inside `Tenent` makes the foundational tenant service depend on services that themselves may depend on tenant context, a circular-dependency risk this repo's CLAUDE.md dependency graph currently avoids |
| Disadvantage of keeping them as 3 separate services | They share one dependency set, one worker infrastructure, one elevated-audit requirement, and one team-ownership boundary ("who is allowed to trigger irreversible tenant-wide operations"). Splitting further would be the same nano-service problem in the other direction — three tiny sagas each needing their own Celery workers, CI, and on-call rotation for no isolation benefit between them |

**A concrete, already-existing integration point:** `Tenent`'s
`app/domain/events.py` already defines `TenantProvisioningStarted`,
`TenantProvisioningCompleted`, and `TenantProvisioningFailed`, and
`TenantProvisioningClient` already fires them — at a service
(`TenantProvisioning`) that was deleted from the repo. `TenantOrchestration`
should be the consumer of these events for its onboarding saga. This
resolves `Implementation-order.md`'s flagged Phase 5 regression (#20)
*without* resurrecting `TenantProvisioning` as a sixth service — the
provisioning step becomes one stage inside this service's onboarding saga
instead of a separate deployable.

**A concrete, already-existing risk this design directly engages:**
`services/Authentication/TODO.md` and ADR 0004 flag `POST
/auth/credentials` as having no auth gate of its own, because "it has to be
callable before any session exists" — but note that *nothing currently
calls it as designed*. `TenantOrchestration`'s onboarding saga is the
first real, legitimate caller: create the tenant (Tenent) → create the
owner's User record (User) → set the owner's initial credential
(Authentication's `/auth/credentials`) → (eventually) send a welcome email
(Notification). Building `TenantOrchestration` makes this a good forcing
function to finally close that gap with real service-to-service trust
(mTLS or a signed service token), rather than leaving `/auth/credentials`
open to the public internet indefinitely.

### Recommended Microservice Name
`TenantOrchestration`

### Responsibilities
- Onboard a new tenant: create the tenant (via `Tenent`), create the
  initial owner's identity (via `User`), set the owner's initial
  credential (via `Authentication`), trigger infra provisioning (the
  successor to the old `TenantProvisioning` — either call a rebuilt
  standalone provisioning worker, or, if provisioning work turns out to be
  simple enough, absorb it as an internal module here; decide based on how
  much infra-provisioning logic actually exists once designed — see
  "Future Split Candidates"), send a welcome notification (once
  Notification Service, Phase 7, exists)
- Offboard a tenant: on receiving `Tenent`'s `status_changed` event to
  `deleted`, start a retention-window timer; on expiry, fan out a hard-purge
  request to every service holding that tenant's data (Tenent, User, IAM,
  Authentication, OrganizationManagement, ObservilityManagement) and record
  the outcome
- Migrate a tenant: move a tenant's data across region/shard/infrastructure
  boundaries — an operator-triggered, heavily-audited, resumable job

### Internal Modules
- `OnboardingSagaService` — drives the create-tenant → create-owner →
  set-credential → provision → notify sequence, one step at a time, with
  per-step retry and a resumable saga state machine (not a single
  synchronous transaction — a partial failure midway must be resumable,
  not silently abandoned)
- `OffboardingService` — retention-window scheduling (Celery beat, matching
  APIGateway's existing Celery pattern) + cross-service hard-purge fan-out
- `MigrationService` — operator-triggered job runner; lower priority to
  build than the other two modules (rare, manually-supervised — see Phase
  sequencing note below)

### Public APIs
- `POST /api/v1/tenant-orchestration/onboard` — kick off onboarding
  (idempotent on a client-supplied idempotency key)
- `GET /api/v1/tenant-orchestration/onboarding/{session_id}` — saga status
- `POST /api/v1/tenant-orchestration/{tenant_id}/offboard` — request
  offboarding (starts the retention countdown, does not purge immediately)
- `GET /api/v1/tenant-orchestration/offboarding/{tenant_id}` — status
- `POST /api/v1/tenant-orchestration/{tenant_id}/migrate` — operator-only,
  should require an elevated permission scope IAM's ABAC engine can
  express (this is exactly the kind of decision `PolicyEvaluationService`
  exists for — see `docs/architecture/abac-policy-management.md`)
- `GET /api/v1/tenant-orchestration/migrations/{job_id}` — status

### Domain Model
- `OnboardingSession` — `id`, `tenant_id` (nullable until the tenant-create
  step completes), `status` (`started/tenant_created/owner_created/
  credential_set/provisioning/notified/completed/failed`), `current_step`,
  `error_detail`, timestamps
- `OffboardingRequest` — `id`, `tenant_id`, `requested_at`,
  `scheduled_purge_at` (retention window), `status`
  (`scheduled/purging/completed/failed`), `purge_results` (JSON, per-service
  outcome)
- `MigrationJob` — `id`, `tenant_id`, `source`, `destination`, `status`
  (`pending/running/completed/failed/rolled_back`), timestamps

### Database Ownership
New Postgres database (`nutratenant_tenant_orchestration`) — owns saga/job
state only, never the tenant aggregate itself (that stays `Tenent`'s).

### Events Published
`tenant_orchestration.onboarding.started/step_completed/completed/failed`,
`tenant_orchestration.offboarding.scheduled/purge_completed/failed`,
`tenant_orchestration.migration.started/completed/failed`

### Events Consumed
- `Tenent`'s existing `TenantProvisioningStarted`/`Completed`/`Failed`
  (already published, currently unconsumed)
- `Tenent`'s tenant `status_changed → deleted` (starts the offboarding
  retention timer)

### Dependencies
`Tenent` (create/read tenant, subscribe to lifecycle events), `User`
(create the owner's identity), `Authentication` (`/auth/credentials` —
requires closing that endpoint's auth gap first, see above), every service
holding tenant-scoped data (offboarding's hard-purge fan-out: IAM,
OrganizationManagement, ObservilityManagement at minimum), Notification
Service once built (Phase 7 — until then, onboarding/offboarding simply
skip the notify step rather than blocking on a service that doesn't exist).

**This is a wide dependency fan-out, and it's the main real cost of this
design** — flagged explicitly, not hidden. It's the correct trade-off
because the alternative (each service exposing its own ad hoc "delete
everything for tenant X" internal-only endpoint that `Tenent` calls
directly) just moves the same fan-out into `Tenent` instead, which is worse
for the reasons in the table above.

### Future Split Candidates
- **`MigrationService`** is the most likely eventual split — it's
  operationally the most different (manually-triggered, rare, DBA-adjacent
  rather than user-facing) and has the weakest shared-lifecycle argument
  with Onboarding/Offboarding of the three. Don't split preemptively —
  there's no volume or ownership pressure yet — but if this platform grows
  to the point of a dedicated infrastructure/ops team distinct from
  product engineering, migration tooling is the natural first thing that
  team owns separately.
- **Infra provisioning**, if it turns out to be substantial (multi-cloud
  resource orchestration, not just a database + a few config rows), may
  warrant re-extracting as its own worker service the way the old
  `TenantProvisioning` was — but only once the actual provisioning logic is
  designed and its complexity is known. Don't resurrect it speculatively.

---

## Phase Sequencing Note

Build `OnboardingSagaService` and `OffboardingService` together (they share
almost everything — worker infra, dependency set, security profile).
`MigrationService` can lag behind; it has no dependency on the other two
modules and no one is blocked waiting for it. See updated
`Implementation-order.md` Phase 5.
