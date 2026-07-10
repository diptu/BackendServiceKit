# 0001. Merge TenantManagement + TenantLifecycle + TenantIsolation into Tenent

Date: 2026-07-05
Status: Accepted

## Context

`TenantManagement` (authoritative CRUD), `TenantLifecycle` (state machine),
and `TenantIsolation` (cross-tenant access enforcement) existed as three
separate deployable services communicating over HTTP. TL had to fail-fast
fetch TM's tenant record over the network, validate transitions against its
own copy of the status, then fire-and-log sync the result back — accepting
that the two copies could drift if that last call failed.

## Decision

Combine all three into one service, `services/Tenent/`, with in-process
calls between what are now `TenantService`, `TenantLifecycleService`, and
`IsolationService` instead of HTTP. `TenantLifecycle`'s `locked` state
becomes a first-class value on the shared `Tenant.status` column instead of
a separately-tracked state proxied across a network boundary.

## Consequences

- No more HTTP clients standing in for "the other service" in tests, and
  no possibility of the two copies drifting — there's only one copy.
- CLAUDE.md's "Service Responsibilities" section describes TM/TL as roles
  within this one service now, not separate ports.
- `docker-compose.yml`'s `tenant-management`/`tenant-lifecycle`/
  `tenant-isolation` service blocks became dead weight pointing at deleted
  directories — cleaned up 2026-07-06 (see the production-readiness audit
  that caught it).
- Full rationale: `services/Tenent/TODO.md`.
