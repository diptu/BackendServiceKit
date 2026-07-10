# API Gateway — TODO

## Siloed Multi-tenancy — Tenant Resolver (access layer)

**Status: implemented (opt-in).** The gateway's half of subdomain routing (root
`README.md` → "Core Architectural Pillars (Target)") is built:

- `TenantResolverMiddleware` (`app/middleware/tenant_resolver.py`) extracts the
  subdomain from the `Host` header and resolves it to a tenant via the Tenent
  Control Plane (`ControlPlaneClient` → `GET /api/v1/control-plane/resolve`).
- The subdomain tenant is the **routing boundary**: it becomes the authoritative
  `X-Tenant-ID` for pre-auth requests, and an authenticated request whose JWT
  tenant differs from the subdomain's tenant is **403'd** (`reconcile_tenant`).
- **Fail closed**: unknown subdomain → 404, Control Plane unreachable → 503.
- Opt-in via `tenant_resolver_enabled` + `gateway_base_domain`; a pass-through
  when off, so existing behaviour is unchanged. 25 tests in
  `tests/unit/test_tenant_resolver.py`; suite 157/157 green.

Remaining for the full north-star:

- [ ] Service-to-service auth so the Control Plane's internal routes
      (`/control-plane/**`, incl. `/dsn`) are never reachable through this
      gateway — the resolver only needs `/resolve`, which is credential-free.
- [ ] Cache subdomain→tenant resolutions (short TTL) to avoid a Control Plane
      round-trip per request under load.

## Active

- [ ] Add JWT bearer-token validation middleware (verify against IAM public key)
- [ ] Implement per-tenant and per-IP rate limiting (Redis sliding window)
- [ ] Add request-size limit middleware (guard against large body attacks)
- [ ] Expose `GET /api/v1/gateway/cache/stats` endpoint (hit/miss counters via Redis)
- [ ] Instrument with OpenTelemetry traces (propagate W3C Trace-Context to upstreams)

## Planned

- [ ] Add route for IAM service when it graduates from Phase 1
- [ ] Circuit breaker per upstream (e.g. tenpy or starlette-circuit-breaker)
- [ ] Retry middleware with exponential back-off for 503/504 responses
- [ ] mTLS between gateway and upstream services
- [ ] Canary routing: split traffic by weight between upstream versions

## Technical Debt

- [ ] Replace fakeredis in tests with testcontainers-redis for true parity
- [ ] Add performance tests (k6/locust) to validate cache hit-rate under load
- [ ] Celery beat schedule for periodic cache warm-up of high-frequency tenant IDs
