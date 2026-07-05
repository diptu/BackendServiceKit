"""FastAPI application factory for OrganizationManagement."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.router import api_router
from app.core.config import settings
from app.core.openapi import TAGS_METADATA
from app.domain.exceptions import (
    OrganizationDeletedError,
    OrganizationNotFoundError,
    OrganizationSlugConflictError,
    TeamNotFoundError,
    TenantNotFoundError,
    TenantServiceUnavailableError,
)
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.core.logging import configure_logging

    configure_logging(debug=settings.debug)
    logger.info(
        "startup", extra={"service": settings.app_name, "version": settings.app_version}
    )

    if settings.enable_tracing:
        try:
            from shared.observability.instrumentation.fastapi import instrument_fastapi
            from shared.observability.instrumentation.httpx import instrument_httpx
            from shared.observability.tracing.propagators import configure_propagator
            from shared.observability.tracing.tracer import configure_tracer

            _tp = configure_tracer(
                settings.app_name, settings.otlp_endpoint, settings.environment
            )
            configure_propagator()
            instrument_fastapi(app, tracer_provider=_tp)
            instrument_httpx()
            logger.info(
                "otel_tracing_enabled", extra={"endpoint": settings.otlp_endpoint}
            )
        except Exception as exc:
            logger.warning("otel_init_failed", extra={"error": str(exc)})

    yield
    logger.info("shutdown", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    app = FastAPI(
        title="Organization Management",
        version=settings.app_version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        openapi_url=None if settings.environment == "production" else "/openapi.json",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    if settings.enable_metrics:
        app.mount("/metrics", make_asgi_app())

    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OrganizationNotFoundError)
    @app.exception_handler(TenantNotFoundError)
    @app.exception_handler(TeamNotFoundError)
    async def _not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(OrganizationSlugConflictError)
    async def _conflict(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(OrganizationDeletedError)
    async def _deleted(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TenantServiceUnavailableError)
    async def _unavailable(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})


app = create_app()
