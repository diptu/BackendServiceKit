# Solution Architecture: ABAC Policy Management

Date: 2026-07-06
Prepared for: `services/AbacPolicyManagement/` (currently a README-only design
doc — no code exists yet)
Scope requested: High-Level Architecture, Service Boundaries, Technology
Choices, Integration Strategy

## The decision this document has to make first

`services/AbacPolicyManagement/README.md` designs **two** services: a
Policy Administration Point (PAP — CRUD, versioning, draft/approval/publish/
rollback) and a Policy Decision Point (PDP — evaluation, simulation,
decision audit). Neither exists as a standalone deployable. But the PDP
role, and a lean version of the PAP role, already exist **inside IAM**:
`services/IAM/app/services/policy_evaluation_service.py` (the real
evaluator — subject+resource attribute matching, RBAC fallback,
default-deny) and `app/api/v1/policies_router.py` (policy CRUD). Built this
session, tested (13 passing tests), already wired through APIGateway at
`/api/v1/policies` and `/api/v1/authorization/evaluate`.

What IAM's version does **not** have, that this README's PAP design calls
for: policy versioning, drafts, an approval workflow, publish/rollback, and
a dedicated decision-audit table. That gap is real — not a documentation
lag, an actual missing capability if your organization needs policy
changes to go through review before they take effect.

So the real question isn't "how do we architect
`services/AbacPolicyManagement`" in isolation — it's **whether policy
governance should be a new service, or a new module inside IAM.** Answering
that changes every section below, so it's answered first.

**Recommendation: extend IAM, do not extract a new service.** Rationale
and alternatives considered follow; if you disagree with this call, the
"Alternative Considered" section below describes what to build instead and
why it costs more than it looks like.

### Why not extract

1. **Evaluation is the hottest, most latency-sensitive path in the
   platform.** Every authorization-sensitive request anywhere in the system
   either calls `PolicyEvaluationService.evaluate()` directly or should.
   Splitting the PDP into its own service turns every one of those calls
   into a network hop (or forces a second cache layer to avoid it — see
   Tenent's `IsolationService` decision cache for how much complexity that
   already adds for one narrower use case). A synchronous authorization
   check is the wrong place to add a new failure domain.
2. **Evaluation reads the same tenant-scoped attribute/role/permission data
   IAM already owns.** A separate PAP+PDP service would need its own copy
   of that data (drift risk — the exact bug class this repo's last audit
   spent most of its effort finding and fixing at *existing* service
   boundaries: `docs/adr/0003-required-tenant-id-on-repositories.md`) or a
   synchronous read-through to IAM on every decision (defeats the point of
   extracting).
3. **No actual scaling or ownership boundary exists yet.** Extraction pays
   for itself when a different team owns policy governance than owns IAM,
   or when policy evaluation load needs to scale independently of IAM's
   other endpoints. Neither is true today — one team, one deploy cadence.

### Alternative considered: full extraction per the original README

Two services, matching the README exactly: `AbacPolicyManagement` (PAP) and
a separate `AbacPolicyEvaluationEngine` (PDP), IAM stops owning policies
entirely.

**Trade-offs if you want this instead:** cleaner textbook PAP/PDP
separation (real value if you're anticipating a dedicated compliance/policy
authoring team later), but pay for it with: a network hop (or a cache with
invalidation events) on every authorization check platform-wide, a second
tenant-scoped datastore to keep consistent with IAM's attribute/role data,
and duplicated tenant-isolation hardening work (ADR 0003) in a second
codebase. Revisit if/when a concrete organizational reason to split
ownership shows up — not preemptively.

---

## High-Level Architecture

Policy governance and policy evaluation become two **modules inside IAM**,
not two services — a module boundary today, so it can become a network
boundary later without a rewrite if the extraction trigger above ever
fires.

```text
                         ┌─────────────────────────────┐
                         │        API Gateway          │
                         │  (JWT-verified, tenant_id    │
                         │   from token, not header)    │
                         └───────────────┬──────────────┘
                                         │
                         ┌───────────────▼──────────────┐
                         │             IAM               │
                         │                                │
                         │  ┌──────────────────────────┐  │
   Policy authors  ─────►│  │ Policy Governance module │  │
   (admin UI/API)         │  │  (PAP)                   │  │
                         │  │  - CRUD (exists today)    │  │
                         │  │  + drafts/versions/       │  │
                         │  │    approval/publish/      │  │
                         │  │    rollback (new)         │  │
                         │  └────────────┬─────────────┘  │
                         │               │ publishes       │
                         │               ▼                 │
                         │  ┌──────────────────────────┐  │
   Every other service  ─┼─►│ Policy Evaluation module │  │
   (in-process if IAM's   │  │  (PDP)                    │  │
    own code; HTTP via     │  │  - evaluate() (exists)    │  │
    gateway otherwise)     │  │  + decision audit table   │  │
                         │  │    (new)                  │  │
                         │  └──────────────────────────┘  │
                         │                                │
                         │        shared: attributes,     │
                         │        roles, permissions,      │
                         │        tenant_id scoping        │
                         └────────────────────────────────┘
```

Both modules read/write the same `abac_policies` table (governance adds
`policy_versions`/`policy_drafts`/`policy_approvals` alongside it) and share
IAM's existing tenant-scoping convention (`tenant_id` required, never
optional — ADR 0003) and its existing `AttributeRepository`/`RoleRepository`
for the data evaluation already depends on.

## Service Boundaries

**Bounded context: IAM owns "who can do what."** This doesn't change — it
already owns identity attributes, roles, permissions, groups, entitlements,
access reviews, and now policy governance/evaluation. Adding policy
governance to IAM doesn't cross a domain boundary; it completes one IAM was
already the natural owner of (per CLAUDE.md's documented authorization flow:
`User → Roles → Permissions → ABAC Policy Engine → Resource`).

**Internal module boundary (not a network one), for future-proofing:**

| Module | Owns | Public interface |
|---|---|---|
| Policy Governance (PAP) | `abac_policies`, `policy_versions`, `policy_drafts`, `policy_approvals` | `POST/GET/PATCH/DELETE /api/v1/policies`, `POST /policies/{id}/submit\|approve\|reject\|publish\|rollback`, `GET /policies/{id}/versions` |
| Policy Evaluation (PDP) | `authorization_decisions` (new, decision audit) | `POST /api/v1/authorization/evaluate`, `POST /authorization/evaluate/batch`, `POST /authorization/simulate` |

**Data ownership rule carried over from the rest of this repo:** no other
service gets a foreign key into these tables. Everything outside IAM
reaches evaluation through the gateway-routed HTTP API
(`/api/v1/authorization/evaluate`, already wired in
`services/APIGateway/app/services/route_service.py`), the same as every
other IAM sub-resource.

**What stays out of scope for this module split:** Policy Simulation
(README's `/authorize/simulate`) and Policy Testing & Validation are listed
separately in `Implementation-order.md` (#139/#140, Phase 3) — build them
as an extension of the Evaluation module once it exists, not a prerequisite
for it.

## Technology Choices

No new technology — this extends IAM's existing, already-working stack
rather than standing up a second one:

| Concern | Choice | Why |
|---|---|---|
| Framework/ORM | FastAPI + SQLAlchemy 2 async (already IAM's stack) | Consistency; no second stack to operate |
| Policy condition storage | JSON column on `abac_policies` (already built) | Already handles `all`/`any`/`eq`/`ne`/`in`/`gt`/`gte`/`lt`/`lte`/`exists` — no need for a rules-engine dependency |
| Draft/approval state | A plain `status` enum column on a new `policy_drafts`/version row (`draft → submitted → approved/rejected → published`, plus `rolled_back`) | Matches this repo's existing convention (e.g. Tenent's tenant lifecycle enum, User's status history) — no workflow-engine dependency justified for a 5-state linear flow |
| Versioning | Append-only `policy_versions` table, `seq`-int primary key | Same pattern as `AuthEvent`/`UserStatusHistory` — reliable ordering across SQLite (tests) and Postgres without relying on second-resolution timestamps |
| Decision audit | New `authorization_decisions` table inside IAM | Same append-only pattern; do **not** build this as a call to the not-yet-centralized Audit Logging service (`Implementation-order.md` Phase 6) — that service should consume this table later, not the other way around |

## Integration Strategy

- **Every other active service reaches evaluation the same way they reach
  any IAM sub-resource today:** through APIGateway, which already verifies
  the caller's JWT and forwards the verified `tenant_id` (ADR 0006) — no
  new trust-boundary work needed, just a new route if evaluation needs a
  path APIGateway doesn't already proxy (it does:
  `/api/v1/authorization` is already registered).
- **In-process callers within IAM itself** (e.g., an access-review flow
  that needs a decision) call `PolicyEvaluationService.evaluate()` directly
  — no HTTP round-trip for IAM's own internal use.
- **Publish/rollback should emit a domain event** (`policy.published`,
  `policy.rolled_back`) on IAM's existing event pattern, even though no
  consumer needs it yet. This is specifically for Tenent's
  `IsolationService`-style decision cache (or a future generalized
  Authorization Decision Cache, `Implementation-order.md` #141) to
  invalidate stale cached decisions when a policy changes — build the event
  now, wire a subscriber later, rather than retrofitting cache invalidation
  after the fact.
- **Approval workflow notifications** (a policy submitted for review should
  notify an approver) depend on the Communications phase
  (`Implementation-order.md` Phase 7, not built yet). Until then, expose
  `GET /policies?status=pending_approval` for polling — don't block this
  module on Notification Service existing first.

## What to tell the `services/AbacPolicyManagement` stub directory

Retire it as a separate service candidate. Replace its `README.md` with a
short pointer to this document and to `services/IAM/TODO.md`, the same way
this repo already handles services that turned out to be delivered inside
another one (see how `services/User/TODO.md` documents the
UserLifecycleManagement/UserProfileManagement merge). Don't leave a stub
directory implying a service will eventually exist at that path if the
actual decision is "this lives in IAM."
