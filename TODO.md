# Project Master Task Board

## APIGateway
# API Gateway — TODO

## Active

- [x] Add JWT bearer-token validation middleware — verifies against
      Authentication's shared HS256 secret locally (not IAM's public key —
      IAM was never the token issuer; Authentication is, see
      services/Authentication/TODO.md). See
      app/services/token_verifier.py + app/api/v1/proxy_router.py. Every
      proxied path except `/api/v1/auth/**` now requires a valid
      `Authorization: Bearer` token, and the verified `tenant_id` claim
      replaces whatever `X-Tenant-ID` the client sent — closes the
      cross-tenant-spoofing finding from this repo's own production-
      readiness audit.
- [ ] Implement per-tenant and per-IP rate limiting (Redis sliding window)
- [ ] Add request-size limit middleware (guard against large body attacks)
- [ ] Expose `GET /api/v1/gateway/cache/stats` endpoint (hit/miss counters via Redis)
- [ ] Instrument with OpenTelemetry traces (propagate W3C Trace-Context to upstreams)

## Planned

- [x] Add route for IAM service when it graduates from Phase 1
- [ ] Circuit breaker per upstream (e.g. tenpy or starlette-circuit-breaker)
- [ ] Retry middleware with exponential back-off for 503/504 responses
- [ ] mTLS between gateway and upstream services
- [ ] Canary routing: split traffic by weight between upstream versions

## Technical Debt

- [ ] Replace fakeredis in tests with testcontainers-redis for true parity
- [ ] Add performance tests (k6/locust) to validate cache hit-rate under load
- [ ] Celery beat schedule for periodic cache warm-up of high-frequency tenant IDs


## Authorization
- [x] ABAC Policy Evaluation Engine built in IAM (`app/services/policy_evaluation_service.py`,
      `POST /api/v1/authorization/evaluate`) — evaluates a condition tree
      against subject attributes (+ optional resource attributes), falls
      back to plain RBAC permission grants, default-denies otherwise. See
      services/IAM/TODO.md for the precedence rule and design notes.


## IAM

- [x] Repositories and services are fully implemented (not stubs — see
      CLAUDE.md, which was corrected to stop describing them as such).
- [x] ABAC Policy Evaluation Engine (see Authorization section above).


## User

- [x] Merges UserManagement + UserLifecycleManagement + UserProfileManagement.
      See services/User/TODO.md.


## Authentication

- [x] New service — identity verification, JWT access tokens + rotating
      revocable refresh tokens, credential storage, password change/reset,
      session listing/revocation, account lockout, audit log. See
      services/Authentication/TODO.md for what's built vs. deferred
      (MFA/OAuth2.1/OIDC/SSO) and the design decisions worth knowing before
      touching this service.

