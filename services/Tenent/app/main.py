"""FastAPI application factory for the combined Tenent service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded  # type: ignore[import-untyped]
from slowapi.middleware import SlowAPIMiddleware  # type: ignore[import-untyped]

from app.api.router import api_router
from app.core.config import settings
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
    logger.info("startup", extra={"service": settings.app_name})
    yield
    logger.info("shutdown", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tenent — Combined Tenant Service",
        version=settings.app_version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        openapi_url=None if settings.environment == "production" else "/openapi.json",
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
    async def _unprocessable(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

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
