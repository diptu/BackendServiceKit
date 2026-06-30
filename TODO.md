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
- [x] (COMPLETED) scaffold service directory and standard folder structure
- [x] (COMPLETED) write pyproject.toml (fastapi asyncpg sqlalchemy alembic redis httpx prometheus-client python-jose slowapi opentelemetry)
- [x] (COMPLETED) write .env.example and .python-version
- [x] (COMPLETED) write Dockerfile (multi-stage build appuser uid 10001)
- [x] (COMPLETED) write entrypoint.sh (alembic upgrade head then uvicorn)
- [x] (COMPLETED) write .dockerignore
- [x] (COMPLETED) write alembic.ini
- [x] (COMPLETED) implement core/config.py with pydantic-settings Settings class (port 8004 redis-db-5)
- [x] (COMPLETED) implement core/constants.py (pagination defaults isolation constants)
- [x] (COMPLETED) implement core/logging.py (structured JSON logging with request_id tenant_id context)
- [x] (COMPLETED) implement core/middleware.py (RequestContextMiddleware X-Request-ID propagation)
- [x] (COMPLETED) implement core/metrics.py (Prometheus counters: decisions_total violations_total latency histograms)
- [x] (COMPLETED) implement core/openapi.py (TAGS_METADATA RESPONSES_READ RESPONSES_WRITE R_403 R_404)
- [x] (COMPLETED) implement domain/enums.py (PolicyType IsolationDecision ResourceType AccessAction)
- [x] (COMPLETED) implement domain/events.py (IsolationViolationDetected ResourceClaimed ResourceClaimReleased PolicyUpdated)
- [x] (COMPLETED) implement domain/exceptions.py (IsolationViolationError PolicyNotFoundError ResourceClaimNotFoundError ResourceClaimConflictError InvalidQueryFilterError ContextResolutionError)
- [x] (COMPLETED) implement infrastructure/database/base.py (DeclarativeBase + MetaData naming convention + TimestampMixin)
- [x] (COMPLETED) implement infrastructure/database/engine.py (async engine pool_size ssl)
- [x] (COMPLETED) implement infrastructure/database/session.py (async_sessionmaker)
- [x] (COMPLETED) implement infrastructure/database/dependencies.py (get_db per-request session)
- [x] (COMPLETED) implement infrastructure/cache/redis_cache.py (fault-tolerant get/set/delete + decision_cache_key claim_cache_key policy_cache_key)
- [x] (COMPLETED) implement infrastructure/clients/tenant_management.py (fire-and-log get_tenant_status for active-tenant guard)
- [x] (COMPLETED) implement infrastructure/messaging/publisher.py (RabbitMQPublisher + NullPublisher)
- [x] (COMPLETED) implement models/isolation_policy.py (SQLAlchemy ORM: id tenant_id name policy_type allow_cross_tenant_read allowed_partner_ids is_active)
- [x] (COMPLETED) implement models/resource_claim.py (SQLAlchemy ORM: id tenant_id resource_id resource_type source_service claimed_at; composite unique idx)
- [x] (COMPLETED) implement models/access_decision_log.py (SQLAlchemy ORM: id caller_tenant_id target_tenant_id resource_id resource_type action decision reason request_id decided_at)
- [x] (COMPLETED) add barrel __init__.py exports for models
- [x] (COMPLETED) implement repositories/base.py (BaseRepository PageResult encode/decode_cursor)
- [x] (COMPLETED) implement repositories/isolation_policy.py (CRUD get_by_tenant list update is_active toggle)
- [x] (COMPLETED) implement repositories/resource_claim.py (claim release get_owner list_by_tenant bulk_claim)
- [x] (COMPLETED) implement repositories/access_decision_log.py (create list_by_tenant list_violations cursor-pagination)
- [x] (COMPLETED) add barrel __init__.py exports for repositories
- [x] (COMPLETED) implement schemas/base.py (AppBaseModel with from_attributes=True populate_by_name=True)
- [x] (COMPLETED) implement schemas/isolation.py (ValidateRequest ValidateResponse CheckAccessRequest CheckAccessResponse ResolveContextRequest ResolveContextResponse ValidateResourceRequest ValidateQueryRequest PolicyResponse PolicyListResponse PolicyUpdateRequest ResourceClaimRequest ResourceClaimResponse AccessDecisionLogResponse)
- [x] (COMPLETED) implement validators/isolation_validator.py (validate_tenant_ids validate_resource_type validate_access_action validate_query_filter validate_policy_update)
- [x] (COMPLETED) implement events/isolation_events.py (EventPublisher publish_event routing keys)
- [x] (COMPLETED) implement dependencies/isolation.py (get_policy_or_404 get_claim_or_404 DbDep PolicyDep)
- [x] (COMPLETED) implement services/isolation_service.py (validate check_access resolve_context validate_resource validate_query list_policies update_policy — Redis-first with DB fallback)
- [x] (COMPLETED) implement services/resource_claim_service.py (claim release get_owner bulk_claim with Redis cache)
- [x] (COMPLETED) implement api/v1/health_router.py (GET /health GET /ready probe DB Redis RabbitMQ)
- [x] (COMPLETED) implement api/v1/isolation_router.py (POST /isolation/validate POST /isolation/check-access POST /isolation/resolve-context POST /isolation/validate-resource POST /isolation/validate-query GET /isolation/policies PATCH /isolation/policies/{id} POST /isolation/claims DELETE /isolation/claims GET /isolation/decisions)
- [x] (COMPLETED) implement api/router.py (include health + isolation routers + GET /metrics)
- [x] (COMPLETED) implement app/main.py (lifespan CORS RequestContextMiddleware slowapi JWT exception handlers metrics OTel)
- [x] (COMPLETED) write Alembic initial migration (isolation_policies resource_claims access_decision_logs tables)
- [x] (COMPLETED) write scripts/bootstrap.sh fix.sh lint.sh
- [x] (COMPLETED) add service to docker-compose.yml (tenant-isolation port 8004 redis-db-5 db nutratenant_isolation)
- [x] (COMPLETED) write unit tests — api endpoints (validate check-access resolve-context policies health metrics)
- [x] (COMPLETED) write unit tests — validators (resource_type action query_filter policy_update)
- [x] (COMPLETED) write integration tests — IsolationService against real SQLite (validate allow deny partner cross-tenant)
- [x] (COMPLETED) write integration tests — ResourceClaimService (claim release get_owner conflict)
- [x] (COMPLETED) write E2E tests — full isolation flow (claim resource → validate access → log decision → check audit trail)
- [x] (COMPLETED) write performance tests — concurrent access checks (cache hit vs miss latency decision throughput)
- [x] (COMPLETED) synchronize master TODO.md via python scripts/todo_manager.py --sync


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
- [x] (COMPLETED) synchronize master TODO.md via python scripts/todo_manager.py --sync


## UserLifecycleManagement


## UserProfileManagement


