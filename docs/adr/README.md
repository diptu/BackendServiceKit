# Architecture Decision Records

Short, dated records of decisions that already happened but previously
existed only as scattered notes in individual services' `TODO.md` files (or
nowhere at all). Each ADR is one page: context, decision, consequences —
not a design spec. For the full rationale behind any of these, follow the
link to the service's own `TODO.md`.

| ID | Title | Status |
|----|-------|--------|
| [0001](0001-merge-tenant-services-into-tenent.md) | Merge TenantManagement + TenantLifecycle + TenantIsolation into Tenent | Accepted |
| [0002](0002-merge-user-services-into-user.md) | Merge UserManagement + UserLifecycleManagement + UserProfileManagement into User | Accepted |
| [0003](0003-required-tenant-id-on-repositories.md) | `tenant_id` is a required repository argument, never optional | Accepted |
| [0004](0004-authentication-service-shared-secret-jwt.md) | Authentication issues shared-secret JWTs; refresh tokens are opaque and revocable | Accepted |
| [0005](0005-iam-abac-engine-rbac-fallback.md) | IAM's ABAC engine falls back to RBAC, then default-denies | Accepted |
| [0006](0006-gateway-enforced-trust-boundary.md) | APIGateway is the only source of truth for `X-Tenant-ID` | Accepted |
| [0007](0007-tenant-orchestration-service-boundary.md) | Onboarding/Offboarding/Migration become one new service (`TenantOrchestration`); Configuration/Compliance extend Tenent | Accepted |
| [0008](0008-abac-policy-management-stays-in-iam.md) | ABAC policy governance extends IAM; `AbacPolicyManagement` is not a new service | Accepted |

## Format

```markdown
# NNNN. Title

Date: YYYY-MM-DD
Status: Accepted | Superseded by NNNN | Deprecated

## Context
What situation forced this decision.

## Decision
What was actually decided.

## Consequences
What this makes easier, harder, or newly possible — including the honest
downsides, not just the upsides.
```

## When to add one

When a decision changes a boundary between services, a data-ownership
rule, or something a future engineer (or agent) would otherwise have to
reverse-engineer from a diff. Not for routine feature work — that belongs
in the PR description and the service's own `TODO.md`.
