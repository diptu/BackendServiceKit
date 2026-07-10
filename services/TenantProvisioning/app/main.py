"""FastAPI application factory for TenantProvisioning."""

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
from app.core.logging import configure_logging
from app.domain.exceptions import (
    ProvisioningInProgressError,
    ProvisioningJobNotFoundError,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(debug=settings.debug)
    logger.info(
        "startup", extra={"service": settings.app_name, "version": settings.app_version}
    )
    yield
    logger.info("shutdown", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tenant Provisioning",
        version=settings.app_version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        openapi_url=None if settings.environment == "production" else "/openapi.json",
        lifespan=lifespan,
    )

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
    @app.exception_handler(ProvisioningJobNotFoundError)
    async def _not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ProvisioningInProgressError)
    async def _conflict(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})


app = create_app()
