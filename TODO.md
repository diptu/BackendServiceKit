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


## TenantIsolation
- [ ] (IN-PROGRESS) Implement Tenant Context Middleware to enforce Tenant ID in all service requests (Due: 2026-06-02)


## TenantLifecycle
# Tenant Lifecycle Service — TODO

- [x] (COMPLETED) implement PUT /tenant-lifecycle/{tenant_id}/provisioning
- [x] (COMPLETED) implement POST /tenant-lifecycle/{tenant_id}/pend
- [x] (COMPLETED) implement PUT /tenant-lifecycle/{tenant_id}/activate
- [x] (COMPLETED) implement PUT /tenant-lifecycle/{tenant_id}/suspend
- [x] (COMPLETED) implement POST /tenant-lifecycle/{tenant_id}/reactivate
- [x] (COMPLETED) implement POST /tenant-lifecycle/{tenant_id}/lock
- [x] (COMPLETED) implement POST /tenant-lifecycle/{tenant_id}/unlock
- [x] (COMPLETED) implement POST /tenant-lifecycle/{tenant_id}/archive
- [x] (COMPLETED) implement POST /tenant-lifecycle/{tenant_id}/delete
- [x] (COMPLETED) implement GET /tenant-lifecycle/{tenant_id}/history


## TenantManagement
# TenantManagement

## Planing
- [x] (Completed) Define business requirements (Phase 1 - Planning)
- [x] (Completed) Define functional requirements (Phase 1 - Planning)
- [x] (Completed) Define non-functional requirements (Phase 1 - Planning)
- [ Completed] Define tenant lifecycle
- [x] (Completed) Define tenant states (Phase 1 - Planning)
- [ ] (PENDING) Define tenant settings (Phase 1 - Planning)
- [ ] (PENDING) Define tenant limits (Phase 1 - Planning)
- [ ] (PENDING) Define tenant metadata (Phase 1 - Planning)
- [ ] (PENDING) Define public APIs (Phase 1 - Planning)
- [ ] (PENDING) Define domain events (Phase 1 - Planning)
- [ ] (PENDING) Define permissions (Phase 1 - Planning)
- [ ] (PENDING) Define ABAC requirements (Phase 1 - Planning)
- [ ] (PENDING) Write README.md (Phase 1 - Planning)
- [ ] (PENDING) Create TODO.md (Phase 1 - Planning)

## API endpoints

### implement following endpoints:

- [x] (COMPLETED) POST /tenants (v1.0-api)
- [x] (COMPLETED) GET /tenants (v1.0 - api)
- [x] (COMPLETED) GET /tenants/{tenant_id} (v1.0- api)
- [x] (COMPLETED) PATCH /tenants/{tenant_id} (v1.0- api)
- [x] (COMPLETED) DELETE /tenants/{tenant_id} (v1.0- api)


## TenantProvisioning
- [x] (COMPLETED) scaffold service directory and standard folder structure
- [x] (COMPLETED) implement core/config.py with pydantic-settings Settings class
- [x] (COMPLETED) implement domain/enums.py (JobStatus StepName ResourceType PROVISIONING_STEPS)
- [x] (COMPLETED) implement domain/exceptions.py (ProvisioningJobNotFoundError TenantProvisioningNotFoundError ProvisioningJobAlreadyActiveError)
- [x] (COMPLETED) implement infrastructure/database/base.py (DeclarativeBase + MetaData naming convention)
- [x] (COMPLETED) implement models/provisioning_job.py (SQLAlchemy ORM with indexes)
- [x] (COMPLETED) implement models/provisioning_resource.py (SQLAlchemy ORM with FK to provisioning_jobs)
- [x] (COMPLETED) implement repositories/provisioning_job.py (CRUD cursor-pagination has_active_job update_status)
- [x] (COMPLETED) implement repositories/provisioning_resource.py
- [x] (COMPLETED) implement schemas/provisioning.py (StartProvisioningRequest JobResponse JobListResponse ResourceResponse TenantProvisioningStatusResponse)
- [x] (COMPLETED) implement services/provisioning_service.py (start retry list get add_resource tenant_status)
- [x] (COMPLETED) implement tasks/worker.py (Celery app definition)
- [x] (COMPLETED) implement tasks/provisioning_tasks.py (run_provisioning task + 8-step _provision_async)
- [x] (COMPLETED) implement infrastructure/clients/tenant_lifecycle.py (fire-and-log advance_to_pending)
- [x] (COMPLETED) implement infrastructure/messaging/consumer.py (TenantEventConsumer aio-pika)
- [x] (COMPLETED) implement infrastructure/messaging/publisher.py (RabbitMQPublisher + NullPublisher)
- [x] (COMPLETED) implement api/v1/provisioning_endpoints.py (POST /tenants GET /jobs GET /jobs/{job_id} POST /tenants/{id}/retry POST /tenants/{id}/resources GET /tenants/{id}/status)
- [x] (COMPLETED) implement app/main.py (lifespan CORS exception handlers)
- [x] (COMPLETED) write Alembic initial migration (provisioning_jobs + provisioning_resources tables)
- [x] (COMPLETED) write Dockerfile (multi-stage build appuser uid 10001)
- [x] (COMPLETED) write entrypoint.sh (alembic upgrade head then uvicorn)
- [x] (COMPLETED) add service to docker-compose.yml (tenant-provisioning port 8003 + tenant-provisioning-worker)
- [x] (COMPLETED) write unit tests - 14 tests all passing
- [x] (COMPLETED) add validators/ layer for domain-level input validation separate from Pydantic schemas
- [x] (COMPLETED) add dependencies/ module with reusable DI for job and tenant existence checks
- [x] (COMPLETED) add events/ module for publishing domain events (job.started job.completed job.failed)
- [x] (COMPLETED) add barrel __init__.py exports for models and repositories
- [x] (COMPLETED) write integration tests (real DB real Celery task execution per-step assertions) - 19 tests
- [x] (COMPLETED) write E2E tests (full flow API to Celery worker to TL advance_to_pending callback) - 7 tests
- [x] (COMPLETED) write performance tests (concurrent provisioning requests queue depth under load) - 6 tests
- [x] (COMPLETED) add structured JSON logging with request_id tenant_id and trace_id context fields
- [x] (COMPLETED) add Prometheus /metrics endpoint (job counts step latencies queue depth)
- [x] (COMPLETED) add OpenTelemetry tracing integration (span per provisioning step)
- [x] (COMPLETED) enhance /ready health check to probe DB Redis and RabbitMQ connectivity
- [x] (COMPLETED) add Redis caching for GET /provisioning/jobs/{job_id} responses with TTL invalidation on status change
- [x] (COMPLETED) add cache invalidation on job status updates in update_status repository method
- [x] (COMPLETED) add JWT bearer token auth middleware to validate all provisioning endpoints
- [x] (COMPLETED) add rate limiting middleware (per-tenant limits on POST /tenants and POST /retry)
- [x] (COMPLETED) add X-Request-ID middleware for request tracing
- [x] (COMPLETED) implement dead letter queue handling for permanently failed Celery tasks (kombu DLX on celery.dlx exchange)
- [x] (COMPLETED) implement resource rollback task to undo provisioned resources on job failure
- [x] (COMPLETED) add Celery retry with exponential backoff for transient infra failures in provisioning steps
- [x] (COMPLETED) add Flower monitoring setup for Celery worker visibility (docker-compose monitoring profile)
- [ ] (PENDING) complete README.md with architecture diagram API reference and env vars table
- [ ] (PENDING) synchronize master TODO.md via python scripts/todo_manager.py --sync


## UserLifecycleManagement


## UserProfileManagement


