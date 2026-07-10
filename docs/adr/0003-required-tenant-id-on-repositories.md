# 0003. `tenant_id` is a required repository argument, never optional

Date: 2026-07-06
Status: Accepted

## Context

A production-readiness audit of this repo found the same bug shape twice
independently: a repository lookup method (`get_by_id`, `get_by_user_id`,
etc.) that took an entity ID but no `tenant_id` filter, even though the
underlying model had a `tenant_id` column. In `services/User`, this let any
tenant read or overwrite another tenant's profile/avatar/preferences/
contacts by guessing a UUID. In `services/Tenent`, the isolation-policy
repository — the code whose entire job is enforcing cross-tenant isolation
— had the identical gap on itself. `services/IAM`'s repositories already
had the *pattern* that causes this (`tenant_id: UUID | None = None`) but
every current call site happened to pass it, so it wasn't yet exploitable
there — just one accidental omission away from being the same bug.

## Decision

Every repository method that scopes a lookup by tenant now takes
`tenant_id` as a required keyword argument — never `| None = None`. Fixed
directly in `services/User` and `services/Tenent`, and hardened
pre-emptively in `services/IAM` (all seven of its repositories) even though
no exploit existed there yet, on the theory that removing the optional
footgun is cheaper than trusting every future caller to remember it.
`services/OrganizationManagement` was audited for the same shape and found
already safe (every call site passes it explicitly) — left as-is rather
than fixing a non-issue, though the optional-parameter *shape* there is the
same latent risk and worth the same treatment eventually.

## Consequences

- A missing `tenant_id` at a call site is now a type error, not a silent
  cross-tenant data leak reachable only by whoever notices the bug in
  testing (or doesn't).
- Every fix shipped with regression tests proving cross-tenant reads return
  defaults/404 and cross-tenant writes fail, not just that the happy path
  still works.
- Doesn't cover every service yet — OrganizationManagement's IAM-shaped
  optional parameters remain optional (currently safe, not yet hardened).
