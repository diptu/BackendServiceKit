# 0006. APIGateway is the only source of truth for `X-Tenant-ID`

Date: 2026-07-06
Status: Accepted

## Context

A production-readiness audit found the single largest gap in this repo:
`APIGateway`'s reverse proxy read `X-Tenant-ID` straight off the incoming
client request and forwarded it verbatim to every upstream service. Every
tenant-scoping check downstream (IAM, User, Tenent, OrganizationManagement)
was enforcing a boundary the caller could simply declare its way around —
none of ADR 0003's tenant-scoping hardening matters if the tenant_id itself
is unauthenticated input.

## Decision

`APIGateway`'s proxy router now requires `Authorization: Bearer
<access_token>` on every proxied path except `/api/v1/auth/**`
(Authentication's own pre-auth endpoints — login/refresh/credentials
can't require a token that doesn't exist yet, and its authenticated
sub-routes already guard themselves via its own dependency, so gating them
again at the gateway would be redundant). The gateway verifies the JWT
locally (shared secret, see ADR 0004) and the verified `tenant_id` claim —
not the client's header — is what gets forwarded upstream and used for
cache keys/invalidation.

## Consequences

- Closes the finding: a client can no longer set `X-Tenant-ID` to whatever
  it wants. Verified end-to-end with a regression test that sends a
  spoofed header alongside a valid token for a different tenant and
  confirms the upstream only ever sees the token's tenant.
- Found and fixed a real bug while building this: naively overwriting the
  header in the forwarded-headers dict left the client's original
  (lower-cased, ASGI-style) key alongside the new one under different
  casing — two dict keys, both sent as separate header lines, silently
  reintroducing the exact spoofing gap this fix exists to close. Fixed by
  explicitly dropping the client-supplied key (case-insensitively) before
  setting the verified one.
- Still HS256/shared-secret (ADR 0004's limitation applies here too) —
  this closes the *unauthenticated* gap, not the "any service holding the
  secret can forge a token" one.
- `services/APIGateway/app/services/token_verifier.py` and
  `app/api/v1/proxy_router.py` are the two files to read for the actual
  mechanism.
