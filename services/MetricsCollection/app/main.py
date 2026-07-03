"""FastAPI application factory for the Metrics Collection service."""

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
from app.core.openapi import TAGS_METADATA
from app.domain.exceptions import (
    BulkPushLimitExceededError,
    InvalidPromQLError,
    NotAnOperatorError,
    PrometheusQueryError,
    PrometheusUnavailableError,
    PushgatewayError,
    PushgatewayUnavailableError,
    ScrapedMetricDeleteNotSupportedError,
)
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.core.logging import configure_logging

    configure_logging(debug=settings.debug)
    logger.info("startup", extra={"service": settings.app_name, "version": settings.app_version})

    app.state.http_client = httpx.AsyncClient(timeout=settings.prometheus_timeout)

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
        title="Metrics Collection — operator-only query/push/export API over Prometheus",
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

    # This service's own self-instrumentation scrape endpoint — separate
    # from the domain API at /api/v1/metrics/* (which is about querying
    # *other* services' metrics, not this one's own).
    if settings.enable_metrics:
        app.mount("/metrics", make_asgi_app())

    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotAnOperatorError)
    async def _forbidden(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ScrapedMetricDeleteNotSupportedError)
    async def _conflict(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(InvalidPromQLError)
    @app.exception_handler(BulkPushLimitExceededError)
    async def _validation(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(PrometheusUnavailableError)
    @app.exception_handler(PushgatewayUnavailableError)
    async def _unavailable(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(PrometheusQueryError)
    @app.exception_handler(PushgatewayError)
    async def _bad_gateway(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})


app = create_app()
