# Implementation Order — Enterprise Multi-Tenant IAM + ABAC SaaS Platform

Produced by the Implementation Planner skill against the approved 150-service
roadmap. This supersedes the previous version of this file, which only
covered 12 services and had gone stale (it still listed IAM as planned and
User as in-progress after both had shipped).

## Executive Summary

**7 of 150 planned services are built and independently tested (442 passing
tests total).** They cover the entire identity/tenant/access foundation —
which is exactly the part of the dependency graph that has to exist before
almost anything else in the list can be built safely. The remaining 143
items are organized below into 12 phases, sequenced so that each phase only
depends on phases that already shipped, with explicit call-outs for where a
planned "service" turned out to be better delivered as a feature inside an
existing one (see "Delivered differently than planned" below) rather than a
150th deployable.

**One item needs attention before Phase 2 starts, not after:** Tenant
Provisioning (#20) was built once, then its source directory was deleted —
but `Tenent`'s `TenantProvisioningClient` and `APIGateway`'s
`/api/v1/provisioning/**` proxy route still call out to it. Right now that's
a silent gap (fire-and-log calls that fail quietly), not a crash, but it's
resolved as part of Phase 5 — see below; a Principal Engineer review
(`docs/adr/0007-tenant-orchestration-service-boundary.md`) found the fix is
a new `TenantOrchestration` service consuming the events `Tenent` already
publishes, not resurrecting `TenantProvisioning` itself.

## Status Legend

| Status | Meaning |
|---|---|
| ✅ Delivered | Built, tested, running as (part of) an active service |
| 🟡 Partial | Some of the capability exists inside another service; not a standalone service and may have real gaps |
| 📝 Planned | Not started — directory under `services/` is README-only |
| ⚠️ Regressed | Was built, then removed; dangling references exist elsewhere in the codebase |

---

## Phase 0 — Foundation (✅ Done)

Not on the original 150-item list, but everything else depends on it:
mono-repo scaffolding, `uv` tooling, per-service Clean Architecture layout,
CI (`ci.yml`, auto-discovers `services/*/pyproject.toml`) and CD (`cd.yml`,
manually-maintained deploy matrix), multi-stage Dockerfiles, `docker-compose.yml`
dev stack, `shared/observability` (OTel SDK, fully implemented and consumed
by every active service).

---

## Phase 1 — Identity & Tenant Core (✅ Done — the critical path)

This phase was the actual critical path: nothing else on the 150-item list
can be built safely without a real tenant boundary, a real user identity,
and a real way to verify who's calling. All of it shipped as **7 services**,
several of which absorbed multiple line items from the original 150 because
splitting them into separate deployables would have meant re-inventing the
same tenant-scoping/auth-verification plumbing 3-4 times over for no
isolation benefit.

| # | Planned service | Status | Delivered as |
|--:|---|---|---|
| 1 | Identity & Access Management (IAM) | ✅ | `services/IAM` |
| 2 | Authentication Service | ✅ | `services/Authentication` |
| 4 | ABAC Policy Management Service | ✅ | IAM (`policies_router.py`) — governance layer (versioning/approval) still open, see ADR 0008 |
| 5 | ABAC Policy Evaluation Engine | ✅ | IAM (`policy_evaluation_service.py`, `POST /api/v1/authorization/evaluate`) |
| 6 | RBAC Management Service | ✅ | IAM (roles + permissions) |
| 8 | User Management Service | ✅ | `services/User` |
| 9 | User Profile Service | ✅ | `services/User` |
| 10 | User Lifecycle Management Service | ✅ | `services/User` |
| 18 | Password Management Service | 🟡 | Authentication (`/auth/password/*`) — recommend NOT extracting; see below |
| 19 | Tenant Management Service | ✅ | `services/Tenent` |
| 21 | Tenant Lifecycle Management Service | ✅ | `services/Tenent` |
| 22 | Tenant Isolation Service | ✅ | `services/Tenent` |
| 23 | Organization Management Service | ✅ | `services/OrganizationManagement` |
| 25 | Team Management Service | 🟡 | OrganizationManagement (`team_service.py`) |
| 26 | Group Management Service | ✅ | IAM |
| 27 | Membership Management Service | ✅ | IAM (tenant memberships) + OrganizationManagement (org memberships) |
| 28 | Invitation Management Service | ✅ | User (platform invitations) + OrganizationManagement (org invitations) |
| 29 | Role Management Service | ✅ | IAM |
| 30 | Permission Management Service | ✅ | IAM |
| 35 | Access Review Service | ✅ | IAM |
| 38 | Entitlement Management Service | ✅ | IAM |
| 96 | API Gateway Service | ✅ | `services/APIGateway` — also enforces the JWT trust boundary (ADR 0006) |
| 71–77 | Monitoring / Logging / Distributed Tracing / Metrics / Alerting / Observability / Health Check | ✅ | `services/ObservilityManagement` (one container, merges all seven) |
| 142 | Attribute Management Service | ✅ | IAM |

**Delivered differently than planned:**

- **#4/#5/#6/#29/#30/#35/#38/#142 all landed inside IAM**, not as separate
  services. IAM's own dependency injection (its repositories, tenant
  scoping, session handling) would have been duplicated by each one if
  split out, for zero real isolation benefit — they share IAM's database
  and are always deployed together. Reconsider only if one of them needs
  independent scaling or a separate team boundary later.
- **#18 (Password Management)** is deliberately *not* a separate service —
  Authentication already owns the only credential store in the platform
  (ADR 0004); splitting password change/reset into its own service would
  mean either giving it its own copy of `Credential` (drift risk) or a
  synchronous network hop for every password operation. Recommend closing
  this line item as "delivered via Authentication," not planning it
  separately.
- **#71–77 (the observability line items)** are one container by design —
  see `services/ObservilityManagement/TODO.md` Decision #1.
- **#25/#27/#28 are "Partial"/split across two services** because the
  concepts genuinely differ: OrganizationManagement's invitations add an
  already-known `user_id` to an org with a role; User's platform
  invitations onboard a brand-new person onto the platform. Keep them
  separate — collapsing them would conflate two different security
  boundaries.

**Gaps still open from Phase 1** (tracked forward, not blocking Phase 2):

- **Tenant Configuration (#149)** — 🟡 Partial. `Tenent` has a
  `tenant_settings` sub-resource; not the richer per-feature configuration
  model the original line item implies. Resolved by extending `Tenent` —
  see Phase 5 and ADR 0007.
- **Session Management (#11)** — 🟡 Partial. Authentication's
  `refresh_tokens` table + `GET /auth/sessions` already cover "list/revoke
  active sessions." What's missing: device fingerprinting, geo/IP anomaly
  flags, and a management UI. Tracked into Phase 2 with Device Management,
  since they're the same underlying data model.
- **Authorization Service (#3)** — 🟡 Partial. IAM's evaluation engine (#5)
  answers "is this allowed," but there's no separately-deployable
  `Authorization` service the way the roadmap names it. Decide in Phase 3
  whether extracting it is worth the operational cost, given #4/#5/#6
  already share IAM's database.

---

## Phase 2 — Extended Authentication (📝 Planned)

**Depends on:** Authentication, IAM (Phase 1). **Blocks:** any enterprise
customer requiring SSO/SCIM before self-serve signup is viable.

| # | Service | Status |
|--:|---|---|
| 11 | Session Management Service (device/geo depth) | 🟡 Partial → deepen here |
| 12 | Device Management Service | 📝 |
| 13 | API Key Management Service | 📝 |
| 14 | OAuth2 / OpenID Connect Service | 📝 |
| 15 | Single Sign-On (SSO) Service | 📝 |
| 16 | SCIM Provisioning Service | 📝 |
| 17 | Multi-Factor Authentication (MFA) Service | 📝 |
| 143 | Attribute Synchronization Service | 📝 |
| 144 | Identity Federation Service | 📝 |
| 145 | External Identity Provider Integration Service | 📝 |

**Sequencing inside this phase:** API Key Management and Device Management
have no dependency on each other or on OAuth2/SSO — parallelizable. MFA
should land before OAuth2/OIDC and SSO (both need MFA as a step-up option
for enterprise auth flows). SCIM and Identity Federation depend on SSO
existing first (SCIM provisions users *for* an SSO connection).

**Prerequisite carried over from Phase 1:** this whole phase issues and
verifies more token types against the same shared-secret HS256 scheme
Authentication uses today (ADR 0004). Move to asymmetric RS256 signing
*before* adding OAuth2/OIDC here — bolting a public IdP-facing flow onto a
shared-secret scheme where every verifying service holds a forgeable key is
a materially bigger risk than it is internally today.

---

## Phase 3 — Deep Authorization (📝 Planned)

**Depends on:** IAM's ABAC engine, Tenent's isolation decision-cache pattern
(both Phase 1).

| # | Service | Status |
|--:|---|---|
| 3 | Authorization Service (extraction decision) | 🟡 → resolve here |
| 7 | ReBAC Management Service | 📝 |
| 34 | Relationship Graph Service | 📝 |
| 31 | Resource Registry Service | 📝 |
| 32 | Resource Ownership Service | 📝 |
| 33 | Resource Sharing Service | 📝 |
| 36 | Access Request Service | 📝 |
| 37 | Access Approval Workflow Service | 📝 |
| 39 | Delegated Administration Service | 📝 |
| 40 | Just-In-Time (JIT) Access Service | 📝 |
| 41 | Privileged Access Management (PAM) Service | 📝 |
| 139 | Policy Simulation Service | 📝 |
| 140 | Policy Testing & Validation Service | 📝 |
| 141 | Authorization Decision Cache Service | 🟡 Partial |

**Critical path inside this phase:** Resource Registry (#31) has to exist
before Resource Ownership (#32) or Resource Sharing (#33) mean anything —
you can't own or share a resource type the platform doesn't know about yet.
ReBAC (#7) and Relationship Graph (#34) are the same underlying capability
(a graph store + traversal queries) and should be built together, not
sequentially. Access Request (#36) → Access Approval Workflow (#37) is a
strict pipeline. JIT (#40) and PAM (#41) both build on Access Approval
Workflow — don't start them before #37 lands.

**#141 (Authorization Decision Cache)** already has a working pattern to
extend: Tenent's `IsolationService` caches allow/deny decisions in Redis
keyed by (caller_tenant, target_tenant, resource, action). Generalizing
that pattern for ABAC decisions (not just isolation ones) is lower-risk
than building a new caching layer from scratch.

**Also decide here (see ADR 0008):** ABAC Policy Management (#4) has a
governance gap — no versioning/drafts/approval workflow — recommended to
be closed by extending IAM's existing policy module, not extracting a new
`AbacPolicyManagement` service. See
`docs/architecture/abac-policy-management.md` for the full evaluation.

---

## Phase 4 — Workspace & Team Depth (📝 Planned)

**Depends on:** OrganizationManagement (Phase 1).

| # | Service | Status |
|--:|---|---|
| 24 | Workspace Management Service | 📝 |
| 25 | Team Management Service (depth beyond current scope) | 🟡 → deepen here |

Small, low-risk phase — mostly extending OrganizationManagement's existing
data model with a workspace layer between org and team. Good candidate to
run in parallel with Phase 3 (different services, no shared dependency
beyond IAM/OrganizationManagement, which are both already done).

---

## Phase 5 — Tenant Lifecycle Operations (📝 Planned)

**Depends on:** Tenent (Phase 1). A Principal Engineer review evaluated all
six items below against Tenent's existing scope — full evaluation in
`docs/architecture/tenant-lifecycle-services.md`, decision recorded in
`docs/adr/0007-tenant-orchestration-service-boundary.md`.

| # | Service | Status | Resolution |
|--:|---|---|---|
| 20 | Tenant Provisioning Service | ⚠️ Regressed — **do this first** | Absorbed into `TenantOrchestration`'s onboarding saga, consuming `Tenent`'s already-published (currently unconsumed) `TenantProvisioningStarted/Completed/Failed` events — not resurrected as its own service |
| 146 | Tenant Onboarding Automation Service | 📝 | New service: `TenantOrchestration` |
| 147 | Tenant Offboarding Service | 📝 | New service: `TenantOrchestration` (same service as #146 — shared worker infra, dependency set, security profile) |
| 148 | Tenant Migration Service | 📝 | New service: `TenantOrchestration` (lowest priority of the three; weakest shared-lifecycle argument — flagged as the most likely future split) |
| 149 | Tenant Configuration Service | 🟡 → deepen here | Extends `Tenent` as a new sub-resource (same shape as existing `TenantSettings`/`TenantMetadata`) — not a new service |
| 150 | Tenant Compliance Service | 📝 | Attestation *data* extends `Tenent`; the compliance *rules engine* belongs in Compliance Management (#85, Phase 6) instead |

**Two services come out of this phase, not six:** `Tenent` gains two new
sub-resources (Configuration, Compliance attestation), and one new service,
**`TenantOrchestration`**, absorbs Onboarding/Offboarding/Migration as
three related sagas — multi-step, multi-service workflows with a
background-worker lifecycle, sharing one dependency set (Tenent, User,
Authentication, and eventually Notification) and one elevated security
profile (irreversible, cross-service operations), which is a different
shape of work than Tenent's aggregate-CRUD and doesn't belong in the same
blast radius.

**Do the #20 resolution first, as part of building `TenantOrchestration`'s
onboarding module** — not as separate prerequisite work. `Tenent` and
`APIGateway` currently have code paths that silently no-op against a
service that doesn't exist; `TenantOrchestration`'s onboarding saga
consuming `Tenent`'s existing (unconsumed) provisioning events is the fix,
not a rebuild of the old standalone `TenantProvisioning` service.

**A concrete forcing function this phase creates:** `TenantOrchestration`'s
onboarding saga is the first legitimate caller of Authentication's `POST
/auth/credentials` (setting the new tenant owner's initial password) —
which currently has no auth gate of its own (ADR 0004 flagged this as the
biggest concrete gap in Authentication's design). Close that gap
(service-to-service trust — mTLS or signed tokens) before or alongside
building `TenantOrchestration`, not after.

---

## Phase 6 — Audit, Compliance & Data Governance (📝 Planned)

**Depends on:** every Phase 1 service (they're the event sources).

| # | Service | Status |
|--:|---|---|
| 66 | Audit Logging Service (centralized) | 🟡 Partial |
| 67 | Compliance Logging Service | 📝 |
| 68 | Security Event Logging Service | 📝 |
| 69 | Activity Tracking Service | 📝 |
| 70 | Change History Service | 📝 |
| 85 | Compliance Management Service | 📝 |
| 86 | Consent Management Service | 📝 |
| 87 | Privacy Management Service | 📝 |
| 88 | Data Governance Service | 📝 |
| 89 | Data Classification Service | 📝 |
| 90 | Data Retention Service | 📝 |
| 91 | Data Residency Service | 📝 |
| 92 | Encryption & Key Management Service | 📝 |
| 93 | Secrets Management Service | 📝 |

**#66 is "Partial," not "Planned," for a reason worth acting on early:**
every active service already has its own local, correctly-append-only
audit table — Authentication's `AuthEvent`, User's `UserStatusHistory`,
Tenent's `AccessDecisionLog`, IAM's audit events. There is no cross-service
audit trail today; a centralized Audit Logging service's first job should
be *consuming* those existing tables/events (via `shared/messaging`, once
it exists — see below), not replacing them. Building it as a green-field
service that ignores the audit data already being produced would be
redundant work and a second source of truth.

**Sequencing:** #67/#68/#69/#70 are all specializations of #66 — build the
centralized pipeline once, then these are mostly filtering/retention-policy
configuration on top of it, not separate pipelines. #92/#93 (encryption and
secrets) should land before #86/#87/#88 (consent/privacy/governance) — the
latter make compliance claims that are only meaningful if the former are
actually enforced. **#85 (Compliance Management)** should read the
per-tenant compliance attestation data Phase 5 adds to `Tenent`, not
duplicate it.

---

## Phase 7 — Communications (📝 Planned)

**Depends on:** User (recipient identity), Authentication (Phase 1).

| # | Service | Status |
|--:|---|---|
| 60 | Email Service | 📝 |
| 61 | SMS Service | 📝 |
| 62 | Push Notification Service | 📝 |
| 63 | Notification Service (aggregator) | 📝 |
| 64 | Communication Preference Service | 📝 |
| 65 | Template Management Service | 📝 |

**This phase closes a real, already-documented gap.** Authentication's
`POST /auth/password/forgot` currently returns the raw reset token directly
in the API response outside production, specifically because no
notification-delivery path exists yet (`services/Authentication/TODO.md`,
follow-up work section). `TenantOrchestration`'s onboarding saga (Phase 5)
also wants a welcome-email step it currently has to skip. Build Email
Service (#60) and Notification Service (#63) first, then wire both of
those already-identified consumers through it.

**Sequencing:** Template Management (#65) and Communication Preference (#64)
have no hard dependency on the channel services (#60/#61/#62) and can be
built in parallel. Notification Service (#63) is the aggregator/router and
should be built last, once at least one real channel (#60) exists to route
to.

---

## Phase 8 — Commerce & Billing (📝 Planned)

**Depends on:** OrganizationManagement/Tenent (the billing unit),
Notification Service (Phase 7, for receipts/dunning emails).

| # | Service | Status |
|--:|---|---|
| 42 | Subscription Management Service | 📝 |
| 43 | Plan Management Service | 📝 |
| 44 | Feature Management Service | 📝 |
| 45 | Feature Flag Service | 📝 |
| 46 | Usage Metering Service | 📝 |
| 47 | Quota Management Service | 📝 |
| 48 | Billing Service | 📝 |
| 49 | Invoicing Service | 📝 |
| 50 | Payment Service | 📝 |
| 51 | Tax Management Service | 📝 |
| 52 | Customer Account Service | 📝 |
| 53 | Customer Portal Service | 📝 |
| 54 | Partner Management Service | 📝 |
| 55 | White-Label Management Service | 📝 |
| 56 | Branding Management (fold into #55) | 📝 |
| 57 | Domain Management Service | 📝 |
| 58 | Custom Domain Verification Service | 📝 |
| 59 | DNS Automation (fold into #57/#58) | 📝 |
| 137 | License Management Service | 📝 |

**Critical path:** Plan Management (#43) → Feature Management (#44) →
Feature Flag (#45) is a strict dependency chain — you can't gate a feature
by plan before plans and features both exist as entities. Subscription
Management (#42) depends on Plan Management (#43) for the same reason.
Usage Metering (#46) → Quota Management (#47) → Billing (#48) → Invoicing
(#49) → Payment (#50) is the revenue pipeline in strict order; Tax
Management (#51) plugs into Invoicing (#49). Customer Portal (#53) is a
consumer of nearly everything else in this phase and should be built last.
Domain Management (#57)/branding (#55/#56) are independent of the billing
chain and fully parallelizable with it.

---

## Phase 9 — Platform Infrastructure & Ops (📝 Planned)

**Depends on:** ObservilityManagement (Phase 1, for ops visibility into
whatever this phase builds).

| # | Service | Status |
|--:|---|---|
| 94 | Configuration Management Service | 📝 |
| 95 | Service Discovery Service | 📝 |
| 97 | Rate Limiting Service (standalone) | 🟡 Partial |
| 98 | Webhook Management Service | 📝 |
| 99 | Event Bus Service | 🟡 Partial |
| 100 | Message Queue Service | 🟡 Partial |
| 101 | Workflow Orchestration Service | 📝 |
| 102 | Background Job Processing Service (standalone) | 🟡 Partial |
| 103 | Scheduler Service | 📝 |
| 114 | Backup Service | 📝 |
| 115 | Disaster Recovery Service | 📝 |
| 116 | Data Synchronization Service | 📝 |
| 128 | Platform Administration Service | 📝 |
| 129 | Infrastructure Management Service | 📝 |
| 130 | Resource Provisioning Service | 📝 |
| 131 | Cost Management Service | 📝 |
| 132 | FinOps Service | 📝 |
| 133 | Multi-Region Deployment Service | 📝 |

**Every "Partial" here is the same story:** the underlying infrastructure
already exists and works (RabbitMQ is live in `docker-compose.yml`, Celery
runs inside APIGateway, `slowapi` rate-limiting is wired per-service — see
ADR 0004's note that Authentication's is the only one actually enforcing a
limit, Tenent's is wired but inert), but there's no *service* wrapping any
of it with its own API for cross-cutting management. This is exactly the
gap `shared/middleware/`, `shared/cache/`, and `shared/messaging/` were
scaffolded for and never filled in (see CLAUDE.md's "Shared Directory"
section) — before building Event Bus (#99) or Message Queue (#100) as new
services, check whether the actual need is a shared library each service
imports, not another network hop.

**Sequencing:** Configuration Management (#94) and Service Discovery (#95)
are foundational to everything else in this phase — Workflow Orchestration
(#101) and Scheduler (#103) both need service discovery to know what
they're orchestrating against. Backup (#114) → Disaster Recovery (#115) is
a strict pair. Cost Management (#131) → FinOps (#132) similarly.

---

## Phase 10 — Data, Search & Growth (📝 Planned)

**Depends on:** Commerce (Phase 8, for customer-facing data), Audit
(Phase 6).

| # | Service | Status |
|--:|---|---|
| 104 | Search Service | 📝 |
| 105 | Reporting Service | 📝 |
| 106 | Analytics Service | 📝 |
| 107 | Dashboard Service | 🟡 Partial |
| 108 | Data Export Service | 📝 |
| 109 | Data Import Service | 📝 |
| 110 | File Storage Service | 📝 |
| 111 | Object Storage Service | 📝 |
| 112 | Document Management Service | 📝 |
| 113 | Media Processing Service | 📝 |
| 117 | Integration Management Service | 📝 |
| 118 | Third-Party Connector Service | 📝 |
| 119 | Marketplace Service | 📝 |
| 120 | AI/ML Service | 📝 |
| 121 | Recommendation Service | 📝 |
| 122 | Knowledge Base Service | 📝 |
| 123 | Support Ticket Service | 📝 |
| 124 | Customer Success Service | 📝 |
| 125 | Product Announcement Service | 📝 |
| 126 | Onboarding Service (standalone) | 🟡 Partial |
| 134 | Business Intelligence Service | 📝 |
| 135 | Customer Data Platform Service | 📝 |
| 136 | CRM Integration Service | 📝 |
| 138 | Data Lifecycle Management Service | 📝 |

**#107 (Dashboard) is "Partial"** because Grafana already exists as
infrastructure (`docker-compose.yml`'s `--profile observability` stack) —
that's an ops dashboard, not a customer-facing one; don't confuse the two
when scoping this line item. **#126 (Onboarding Service) is distinct from
Phase 5's `TenantOrchestration`** — that one onboards a *tenant* (the
paying customer account); this one is the in-product user-onboarding
experience (checklists, product tours) — don't conflate them when scoping
either. **File Storage (#110) → Object Storage (#111) → Document
Management (#112)/Media Processing (#113)** is a strict layering — the
latter two are consumers of the storage layer, not independent. Search
(#104) depends on there being real data to index — sequence it after at
least Document Management (#112) exists, not before. This whole phase is
the least dependency-constrained relative to each other; the real
constraint is everything upstream (Phases 1-9) needs to exist to have data
worth analyzing/searching/reporting on.

---

## Phase 11 — Security & Trust Operations (📝 Planned)

**Depends on:** ObservilityManagement, Audit Logging (Phase 6).

| # | Service | Status |
|--:|---|---|
| 78 | Incident Management Service | 📝 |
| 79 | Security Center Service | 📝 |
| 80 | Threat Detection Service | 📝 |
| 81 | Anomaly Detection Service | 📝 |
| 82 | Fraud Detection Service | 📝 |
| 83 | Vulnerability Management Service | 📝 |
| 84 | Security Policy Enforcement Service | 📝 |

Deliberately sequenced last, not because it's unimportant, but because
threat/anomaly/fraud detection need a real corpus of audit and metrics data
(Phase 6, Phase 1's observability stack) to detect anything against — built
before that data exists, this phase would just be unvalidated rule engines.
Security Policy Enforcement (#84) is the exception: it could reasonably
move earlier if a specific compliance deadline demands it, since it mostly
consumes IAM's existing ABAC engine (Phase 1) rather than needing new
detection data.

---

## Dependency Flow (updated)

```text
Phase 0: Foundation
   │
Phase 1: IAM ─┬─ Authentication ─┬─ User ─┬─ Tenent ─┬─ OrganizationManagement
              │                  │        │          │
              └─ APIGateway ─────┴────────┴──────────┴─ ObservilityManagement
                      │
        ┌─────────────┼─────────────────────────────┐
        ▼             ▼                              ▼
Phase 2: Ext. Auth   Phase 3: Deep AuthZ      Phase 4: Workspace/Team
  (OAuth2/SSO/MFA)     (ReBAC/PAM/JIT)          (parallel with Phase 3)
        │                     │
        └──────────┬──────────┘
                    ▼
        Phase 5: TenantOrchestration
      (Onboarding/Offboarding/Migration)
   + Tenent gains Configuration/Compliance
                    │
                    ▼
        Phase 6: Audit/Compliance/Governance
                    │
                    ▼
        Phase 7: Communications
                    │
                    ▼
        Phase 8: Commerce & Billing
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Phase 9:     Phase 10:    Phase 11:
   Platform     Data/Search/  Security &
   Infra & Ops  Growth        Trust Ops
```

---

## Parallel Work Opportunities

- **Phase 3 (Deep Authorization) and Phase 4 (Workspace/Team)** have no
  shared dependency beyond Phase 1 — different teams can run these fully
  in parallel.
- **Phase 9 (Platform Infra)** doesn't depend on Phases 6-8 at all — it
  only needs Phase 1's observability stack. It can start as soon as Phase 5
  closes, in parallel with Phases 6-8, if headcount allows.
- Within Phase 8, **Domain Management/branding (#55-59)** is independent of
  the **billing pipeline (#42-51)** — same phase, no shared dependency,
  fully parallelizable.
- Within Phase 2, **API Key Management (#13)** and **Device Management
  (#12)** are independent of the **OAuth2/SSO/SCIM chain (#14-16)**.
- Within Phase 5, **`TenantOrchestration`'s Migration module** has no
  dependency on its Onboarding/Offboarding modules and can lag behind them
  without blocking anything else.

## Technical Risks

1. **Shared-secret JWT (HS256) doesn't scale to Phase 2's OAuth2/OIDC/SSO
   work.** Every service holding `SECRET_KEY` can currently forge a token,
   not just verify one. Low risk today (7 trusted internal services); high
   risk once Phase 2 exposes token issuance to third-party IdPs. Move to
   RS256 before starting Phase 2, not after.
2. **Tenant Provisioning's regression (#20, Phase 5)** is a live gap right
   now, not a future risk — `Tenent` and `APIGateway` both have code paths
   that silently no-op against a service that doesn't exist. Resolved by
   `TenantOrchestration` consuming Tenent's existing events (ADR 0007), not
   by rebuilding the old service.
3. **`Authentication`'s `POST /auth/credentials` has no auth gate**, and
   Phase 5's `TenantOrchestration` becomes its first real caller — close
   the service-to-service trust gap (mTLS/signed tokens) before or
   alongside Phase 5, not after.
4. **No centralized audit trail (#66) despite good per-service audit
   tables.** Phase 6 risks becoming a rebuild instead of a consolidation if
   it doesn't start from the existing `AuthEvent`/`UserStatusHistory`/
   `AccessDecisionLog` tables.
5. **`shared/cache`, `shared/messaging`, `shared/middleware` are still
   empty.** Phase 9's Event Bus/Message Queue/Rate Limiting line items risk
   becoming redundant new services if the real fix is filling in these
   shared libraries instead — decide explicitly, don't default to "new
   service" for each one.
6. **ObservilityManagement's `domains/<bounded-context>/` layout diverges**
   from every other service's horizontal layering. Not a blocker, but
   undocumented drift that costs onboarding time for whoever builds Phase
   9/11 on top of it.

## Production Readiness Gates

Before any phase past Phase 1 is considered production-ready:

- [ ] JWT signing moved to RS256 (blocks Phase 2)
- [ ] Tenant Provisioning regression resolved via `TenantOrchestration`
      consuming Tenent's existing events, not a standalone rebuild (blocks Phase 5)
- [ ] Authentication's `/auth/credentials` gated by real service-to-service
      trust before `TenantOrchestration` becomes its first caller (Phase 5)
- [ ] Centralized audit consumes existing per-service audit tables, doesn't replace them (Phase 6)
- [ ] `shared/cache`/`shared/messaging`/`shared/middleware` decision made explicitly before Phase 9 builds redundant services
- [ ] Every new service follows Phase 1's established conventions: `tenant_id` required (not optional) on every repository lookup, `scripts/fix.sh`/`lint.sh` present, `mypy`/`ruff` declared in its own `pyproject.toml` dev dependencies (not inherited from a system install), horizontal Clean Architecture layout unless explicitly documented otherwise

## Status Workflow

| Status | Meaning |
| -------------- | ---------------------------------------------------------- |
| 📋 Backlog | Future work, not prioritized yet |
| 📝 Planned | Prioritized and ready for implementation |
| 🎨 Designing | Requirements, API contracts, database schema, architecture |
| 🚧 In Progress | Actively being developed |
| 🧪 Testing | Unit, integration, and security testing |
| 👀 Code Review | Awaiting review or refactoring |
| ✅ Completed | Feature implemented and tested |
| 🚀 Deployed | Running in the target environment |
| 🔧 Maintenance | Bug fixes, improvements, and optimizations |
| ❄️ On Hold | Temporarily paused |
| ❌ Cancelled | No longer planned |
