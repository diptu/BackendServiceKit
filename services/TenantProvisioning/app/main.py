"""FastAPI application factory for the Tenant Provisioning service."""

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
    ProvisioningJobAlreadyActiveError,
    ProvisioningJobNotFoundError,
    ProvisioningValidationError,
    TenantProvisioningNotFoundError,
)
from app.infrastructure.database.engine import engine
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)

_consumer = None
_rabbitmq_connection = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _consumer, _rabbitmq_connection

    configure_logging(debug=settings.debug)

    if settings.enable_tracing:
        from app.core.tracing import configure_tracing
        configure_tracing(
            service_name=settings.app_name,
            endpoint=settings.otlp_endpoint,
            enabled=True,
        )

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

        from app.infrastructure.messaging.consumer import TenantEventConsumer
        from app.infrastructure.messaging.publisher import RabbitMQPublisher
        from app.infrastructure.database.session import SessionLocal
        from app.services.provisioning_service import ProvisioningService

        app.state.publisher = RabbitMQPublisher(_rabbitmq_connection)

        async def _trigger_provisioning(tenant_id: object) -> None:
            from uuid import UUID
            tid = UUID(str(tenant_id))
            async with SessionLocal() as session:
                try:
                    svc = ProvisioningService(session, publisher=app.state.publisher)
                    await svc.start_provisioning(tid)
                except ProvisioningJobAlreadyActiveError:
                    logger.info(
                        "consumer_job_already_active",
                        extra={"tenant_id": str(tid)},
                    )
                except Exception as exc:
                    logger.warning(
                        "consumer_trigger_error",
                        extra={"tenant_id": str(tid), "error": str(exc)},
                    )

        _consumer = TenantEventConsumer(_rabbitmq_connection, _trigger_provisioning)
        await _consumer.start()
    except Exception as exc:
        logger.warning(
            "rabbitmq_unavailable_degraded_mode",
            extra={"error": str(exc)},
        )
        app.state.publisher = None

    yield

    if _consumer:
        await _consumer.stop()
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
    title="Tenant Provisioning Service",
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


@app.exception_handler(ProvisioningValidationError)
async def validation_error(
    request: Request, exc: ProvisioningValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": "PROVISIONING_VALIDATION_ERROR"},
    )


@app.exception_handler(ProvisioningJobNotFoundError)
async def job_not_found(request: Request, exc: ProvisioningJobNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TenantProvisioningNotFoundError)
async def tenant_not_found(
    request: Request, exc: TenantProvisioningNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ProvisioningJobAlreadyActiveError)
async def job_already_active(
    request: Request, exc: ProvisioningJobAlreadyActiveError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "error_code": "PROVISIONING_JOB_ALREADY_ACTIVE",
        },
    )


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(api_router)
