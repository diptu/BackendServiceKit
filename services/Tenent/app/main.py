"""FastAPI application factory for the combined Tenent service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from slowapi.errors import RateLimitExceeded  # type: ignore[import-untyped]
from slowapi.middleware import SlowAPIMiddleware  # type: ignore[import-untyped]

from app.api.router import api_router
from app.core.config import settings
from app.core.metrics import REGISTRY
from app.core.openapi import TAGS_METADATA
from app.domain.exceptions import (
    ContextResolutionError,
    InvalidLifecycleTransitionError,
    InvalidQueryFilterError,
    InvalidTenantTransitionError,
    IsolationValidationError,
    IsolationViolationError,
    PolicyNotFoundError,
    ResourceClaimConflictError,
    ResourceClaimNotFoundError,
    TenantContactConflictError,
    TenantContactNotFoundError,
    TenantDeletedError,
    TenantLifecycleAlreadyExistsError,
    TenantLifecycleNotFoundError,
    TenantNameConflictError,
    TenantNotFoundError,
    TenantOwnerRequiredError,
)
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.core.logging import configure_logging

    configure_logging(debug=settings.debug)
    logger.info(
        "startup", extra={"service": settings.app_name, "version": settings.app_version}
    )

    # ── Redis warm-up (fault-tolerant) ───────────────────────────────────
    try:
        from app.infrastructure.cache.redis_cache import get_redis

        await get_redis().ping()
        logger.info("redis_connected", extra={"url": settings.redis_url})
    except Exception as exc:
        logger.warning("redis_unavailable", extra={"error": str(exc)})

    # ── OpenTelemetry ────────────────────────────────────────────────────
    if settings.enable_tracing:
        try:
            from shared.observability.tracing.tracer import configure_tracer
            from shared.observability.tracing.propagators import configure_propagator
            from shared.observability.instrumentation.fastapi import instrument_fastapi
            from shared.observability.instrumentation.httpx import instrument_httpx
            from shared.observability.instrumentation.redis import instrument_redis

            _tp = configure_tracer(
                settings.app_name, settings.otlp_endpoint, settings.environment
            )
            configure_propagator()
            instrument_fastapi(app, tracer_provider=_tp)
            instrument_httpx()
            instrument_redis()
            logger.info(
                "otel_tracing_enabled", extra={"endpoint": settings.otlp_endpoint}
            )
        except Exception as exc:
            logger.warning("otel_init_failed", extra={"error": str(exc)})

    yield
    logger.info("shutdown", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tenent — Combined Tenant Service",
        version=settings.app_version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        openapi_url=None if settings.environment == "production" else "/openapi.json",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    # Middleware (added in reverse execution order)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # Routers
    app.include_router(api_router)

    # Prometheus scrape endpoint backed by the custom isolation REGISTRY
    if settings.enable_metrics:
        app.mount("/metrics", make_asgi_app(registry=REGISTRY))

    # Exception handlers
    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})

    @app.exception_handler(TenantNotFoundError)
    @app.exception_handler(TenantLifecycleNotFoundError)
    @app.exception_handler(PolicyNotFoundError)
    @app.exception_handler(ResourceClaimNotFoundError)
    @app.exception_handler(TenantContactNotFoundError)
    async def _not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TenantNameConflictError)
    @app.exception_handler(TenantContactConflictError)
    @app.exception_handler(ResourceClaimConflictError)
    @app.exception_handler(TenantLifecycleAlreadyExistsError)
    @app.exception_handler(TenantOwnerRequiredError)
    async def _conflict(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(InvalidTenantTransitionError)
    @app.exception_handler(InvalidLifecycleTransitionError)
    async def _conflict_transition(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(IsolationViolationError)
    async def _forbidden(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ContextResolutionError)
    async def _unauthorized(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(TenantDeletedError)
    async def _deleted(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=410, content={"detail": str(exc)})

    @app.exception_handler(InvalidQueryFilterError)
    @app.exception_handler(IsolationValidationError)
    async def _validation(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})


app = create_app()
