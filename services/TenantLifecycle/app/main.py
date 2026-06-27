"""FastAPI application factory for the Tenant Lifecycle Service."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.openapi import TAGS_METADATA
from app.domain.exceptions import (
    InvalidLifecycleTransitionError,
    TenantLifecycleAlreadyExistsError,
    TenantLifecycleNotFoundError,
)
from app.infrastructure.database.engine import engine

logger = logging.getLogger(__name__)

_DESCRIPTION = """\
## Overview

The **Tenant Lifecycle Service** drives and records all lifecycle state transitions
for tenants on the SaaS platform.

It listens to both direct API calls and external billing/subscription events to
transition tenants through their lifecycle states and maintain a complete audit log.

---

## State Machine

```
provisioning → active
active   → suspended | locked | archived
suspended → active | archived
locked   → archived
archived → deleted
```

The `deleted` state is terminal — no further transitions are permitted.

---

## Events Consumed

| Event                  | Action                        |
|------------------------|-------------------------------|
| `subscription.expired` | Suspend tenant automatically  |
| `payment.failed`       | Suspend after N failures      |
| `tenant.offboarded`    | Delete after offboarding      |

---

## Authentication

All endpoints require a valid **bearer token** issued by the Authentication Service.
Only **platform administrators** may trigger lifecycle transitions.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage service-level resources for the duration of the process."""
    configure_logging(debug=settings.debug)
    logger.info(
        "Service starting",
        extra={
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    )

    yield

    await engine.dispose()
    logger.info("Service shutdown complete", extra={"service": settings.app_name})


_docs_url = None if settings.environment == "production" else "/docs"
_redoc_url = None if settings.environment == "production" else "/redoc"
_openapi_url = None if settings.environment == "production" else "/openapi.json"

app = FastAPI(
    title="Tenant Lifecycle Service",
    description=_DESCRIPTION,
    version=settings.app_version,
    contact={
        "name": "Platform Engineering",
        "email": "platform@nutratenant.io",
    },
    license_info={"name": "Proprietary"},
    openapi_tags=TAGS_METADATA,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
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


# ---------------------------------------------------------------------------
# Domain exception → HTTP response handlers
# ---------------------------------------------------------------------------


@app.exception_handler(TenantLifecycleNotFoundError)
async def _not_found(_: Request, exc: TenantLifecycleNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidLifecycleTransitionError)
async def _invalid_transition(
    _: Request, exc: InvalidLifecycleTransitionError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(TenantLifecycleAlreadyExistsError)
async def _already_exists(
    _: Request, exc: TenantLifecycleAlreadyExistsError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={"path": request.url.path, "method": request.method},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )
