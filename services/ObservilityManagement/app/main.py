"""FastAPI application factory for ObservilityManagement — the merged
Logging + DistributedTracing + MetricsCollection + Monitoring + Alerting +
Observability + HealthCheck service. See TODO.md Decision #1."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import NotAnOperatorError
from app.core.openapi import TAGS_METADATA
from app.domains.alerting.exceptions import (
    AlertmanagerError,
    AlertmanagerUnavailableError,
    AlertNotFoundError,
    PrometheusError,
    PrometheusUnavailableError,
    RuleAlreadyExistsError,
    RuleNotFoundError,
    RuleNotManagedError,
)
from app.domains.health.exceptions import UnknownServiceError
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.core.logging import configure_logging

    configure_logging(debug=settings.debug)
    logger.info("startup", extra={"service": settings.app_name, "version": settings.app_version})

    # One shared httpx.AsyncClient for every domain's outbound calls
    # (tier-1 raw backends and external services alike) — TODO.md Decision #3.
    app.state.http_client = httpx.AsyncClient(timeout=settings.sibling_timeout)

    if settings.enable_tracing:
        try:
            from shared.observability.instrumentation.fastapi import instrument_fastapi
            from shared.observability.instrumentation.httpx import instrument_httpx
            from shared.observability.tracing.propagators import configure_propagator
            from shared.observability.tracing.tracer import configure_tracer

            _tp = configure_tracer(settings.app_name, settings.otlp_endpoint, settings.environment)
            configure_propagator()
            instrument_fastapi(app, tracer_provider=_tp)
            instrument_httpx()
            logger.info("otel_tracing_enabled", extra={"endpoint": settings.otlp_endpoint})
        except Exception as exc:
            logger.warning("otel_init_failed", extra={"error": str(exc)})

    yield

    await app.state.http_client.aclose()
    logger.info("shutdown", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    app = FastAPI(
        title="ObservilityManagement — merged observability platform service",
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
    @app.exception_handler(NotAnOperatorError)
    async def _forbidden(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(AlertNotFoundError)
    @app.exception_handler(RuleNotFoundError)
    @app.exception_handler(UnknownServiceError)
    async def _not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RuleAlreadyExistsError)
    @app.exception_handler(RuleNotManagedError)
    async def _conflict(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(AlertmanagerUnavailableError)
    @app.exception_handler(PrometheusUnavailableError)
    async def _unavailable(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(AlertmanagerError)
    @app.exception_handler(PrometheusError)
    async def _bad_gateway(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})


app = create_app()
