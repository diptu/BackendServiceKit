# Project Master Task Board

## APIGateway
# API Gateway — TODO

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


## Authorization
- [ ] (PENDING) Integrate ABAC Policy Engine with Tenant/Org attributes (Due: 2026-06-02)


## IAM


## UserLifecycleManagement


## UserProfileManagement


