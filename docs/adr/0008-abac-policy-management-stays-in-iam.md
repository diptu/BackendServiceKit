# 0008. ABAC policy governance extends IAM; `AbacPolicyManagement` is not a new service

Date: 2026-07-06
Status: Accepted

## Context

`services/AbacPolicyManagement/README.md` designs two services: a Policy
Administration Point (policy CRUD, versioning, draft/approval/publish/
rollback) and a Policy Decision Point (evaluation, simulation, decision
audit). Neither exists standalone — but a lean version of both already
lives inside IAM (`policies_router.py`, `PolicyEvaluationService` — ADR
0005), missing only the governance layer (versioning/drafts/approval/
rollback) the original design calls for.

## Decision

Extend IAM with a Policy Governance module (versioning, drafts, approval
workflow, publish/rollback) alongside its existing Policy Evaluation
module, rather than extracting either into a new service. Full evaluation:
`docs/architecture/abac-policy-management.md`.

## Consequences

- Policy evaluation stays in-process/same-database with the attribute,
  role, and permission data it reads on every authorization check — no
  network hop on the platform's hottest, most latency-sensitive path.
- No second tenant-scoped datastore to keep consistent with IAM's existing
  data (the drift risk ADR 0003 was written to close).
- `services/AbacPolicyManagement/README.md` should be replaced with a
  pointer to this ADR and to `services/IAM/TODO.md` — it should stop
  implying a service will eventually exist at that path.
- Revisit only if a genuine organizational reason to split policy
  governance ownership from IAM engineering emerges — not preemptively.
