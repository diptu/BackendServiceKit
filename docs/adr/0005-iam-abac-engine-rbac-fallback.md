# 0005. IAM's ABAC engine falls back to RBAC, then default-denies

Date: 2026-07-06
Status: Accepted

## Context

IAM had a fully implemented data model for roles, permissions, attributes,
entitlements, and groups, but nothing that actually evaluated a policy
against a request and returned an allow/deny decision — the authorization
flow CLAUDE.md documented (`User → Roles → Permissions → ABAC Policy Engine
→ Resource`) stopped at the data layer.

## Decision

Built `PolicyEvaluationService.evaluate()` (`services/IAM/app/services/
policy_evaluation_service.py`) with this precedence, evaluated in order and
stopping at the first thing that decides:

1. Merge the subject's ABAC attributes with any caller-supplied resource
   attributes (resource context wins a key collision).
2. Evaluate this tenant's active `AbacPolicy` rows matching
   resource_type+action, ordered priority-DESC, deny-before-allow at a tie,
   newest-first as final tiebreak. First matching policy's effect decides.
   A policy with no conditions matches unconditionally.
3. If no ABAC policy matched, fall back to plain RBAC: does any role
   assigned to the user carry a permission named `"{resource_type}:{action}"`?
4. Otherwise, default-deny.

An explicit ABAC policy (allow or deny) always overrides the RBAC
fallback — ABAC is a refinement layer on top of RBAC's coarser grant, not a
parallel, independent check.

## Consequences

- Authorization decisions are now actually enforceable, not just
  data-modeled. `POST /api/v1/authorization/evaluate` is a real endpoint.
- The precedence rule is a judgment call, not something enforced by any
  external spec — worth revisiting if a future policy author's mental
  model doesn't match "ABAC always overrides RBAC."
- Every `PolicyRepository` method requires `tenant_id` (ADR 0003) —
  written correctly from the start rather than needing a later fix.
- Full detail: `services/IAM/TODO.md`.
