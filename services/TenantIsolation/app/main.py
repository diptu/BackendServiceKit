"""FastAPI application factory for the Tenant Isolation service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler  # type: ignore[import-untyped]
from slowapi.errors import RateLimitExceeded  # type: ignore[import-untyped]

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.openapi import TAGS_METADATA
from app.domain.exceptions import (
    ContextResolutionError,
    InvalidQueryFilterError,
    IsolationValidationError,
    IsolationViolationError,
    PolicyNotFoundError,
    ResourceClaimConflictError,
    ResourceClaimNotFoundError,
)
from app.infrastructure.database.engine import engine
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)

_rabbitmq_connection = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _rabbitmq_connection

    configure_logging(debug=settings.debug)

    if settings.enable_tracing:
        try:
            from opentelemetry import trace  # type: ignore[import-untyped]
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-untyped]
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-untyped]
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore[import-untyped]

            provider = TracerProvider()
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint))
            )
            trace.set_tracer_provider(provider)
        except Exception as exc:
            logger.warning("tracing_setup_failed", extra={"error": str(exc)})

    logger.info(
        "startup",
        extra={
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    )

    try:
        import aio_pika

        _rabbitmq_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        from app.infrastructure.messaging.publisher import RabbitMQPublisher

        app.state.publisher = RabbitMQPublisher(_rabbitmq_connection)
    except Exception as exc:
        logger.warning(
            "rabbitmq_unavailable_degraded_mode",
            extra={"error": str(exc)},
        )
        app.state.publisher = None

    yield

    if _rabbitmq_connection:
        await _rabbitmq_connection.close()
    await engine.dispose()
    logger.info("shutdown", extra={"service": settings.app_name})


_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if settings.environment == "production"
    else {}
)

app = FastAPI(
    title="Tenant Isolation Service",
    version=settings.app_version,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    **_docs_kwargs,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IsolationViolationError)
async def isolation_violation(
    request: Request, exc: IsolationViolationError
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "error_code": "ISOLATION_VIOLATION"},
    )


@app.exception_handler(PolicyNotFoundError)
async def policy_not_found(request: Request, exc: PolicyNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ResourceClaimNotFoundError)
async def claim_not_found(
    request: Request, exc: ResourceClaimNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ResourceClaimConflictError)
async def claim_conflict(
    request: Request, exc: ResourceClaimConflictError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "error_code": "RESOURCE_CLAIM_CONFLICT"},
    )


@app.exception_handler(InvalidQueryFilterError)
async def invalid_query_filter(
    request: Request, exc: InvalidQueryFilterError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": "INVALID_QUERY_FILTER"},
    )


@app.exception_handler(ContextResolutionError)
async def context_resolution_error(
    request: Request, exc: ContextResolutionError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc), "error_code": "CONTEXT_RESOLUTION_ERROR"},
    )


@app.exception_handler(IsolationValidationError)
async def isolation_validation(
    request: Request, exc: IsolationValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": "ISOLATION_VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(api_router)
