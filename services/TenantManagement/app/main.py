"""FastAPI application factory for the Tenant Management Service."""

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
    InvalidTenantTransitionError,
    TenantContactConflictError,
    TenantContactNotFoundError,
    TenantLockedError,
    TenantNameConflictError,
    TenantNotFoundError,
    TenantOwnerRequiredError,
    TenantSlugConflictError,
)
from app.infrastructure.database.engine import engine

logger = logging.getLogger(__name__)

_DESCRIPTION = """\
## Overview

The **Tenant Management Service** is the system of record for all tenant data on the
SaaS platform. It owns the complete lifecycle, configuration, ownership, and metadata
for every customer (tenant).

A **tenant** is the top-level isolation boundary — every organization, workspace,
resource, and user is ultimately scoped to a tenant.

---

## Authentication

All endpoints require a valid **bearer token** issued by the Authentication Service:

```
Authorization: Bearer <token>
```

Unauthenticated requests receive `401 Unauthorized`.
Requests lacking the required role receive `403 Forbidden`.

---

## Authorization

Only **platform administrators** may:

- Create tenants
- Delete tenants
- Trigger lifecycle transitions (suspend, archive)
- Modify tenant ownership

---

## Tenant Lifecycle

```
draft → provisioning → active
                          ↓
                      suspended → active  (reactivation)
                          ↓
                      archived → deleted
```

- **active**: fully operational; all APIs enabled.
- **suspended**: login and API access blocked; data preserved.
- **archived**: read-only; all writes return `423 Locked`.
- **deleted**: soft-deleted; name is reserved until hard-deletion by the Offboarding Service.

---

## Rate Limiting

| Endpoint class   | Limit          |
|------------------|----------------|
| Read endpoints   | 1 000 req/min  |
| Write endpoints  |   100 req/min  |
| Admin endpoints  |    50 req/min  |

Rate-limited requests receive `429 Too Many Requests` with a `Retry-After` header.

---

## Pagination

List endpoints support **cursor-based pagination**:

```
GET /api/v1/tenants?limit=20&cursor=<opaque_cursor>
```

Response includes `cursor`, `has_more`, and `total`.

---

## API Versioning

This service is currently at **v1**. All endpoints are prefixed `/api/v1/`.
Breaking changes will introduce a new version prefix. The previous version remains
supported for a minimum of **6 months** after deprecation notice.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage service-level resources for the duration of the process.

    Startup:
        - Configures structured JSON logging.
        - Logs a startup event with service metadata.

    Shutdown:
        - Disposes the SQLAlchemy async engine (drains the connection pool).
        - Logs a shutdown event.
    """
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
    title="Tenant Management Service",
    description=_DESCRIPTION,
    version=settings.app_version,
    contact={
        "name": "Platform Engineering",
        "email": "platform@nutratenant.io",
    },
    license_info={
        "name": "Proprietary",
    },
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


@app.exception_handler(TenantNotFoundError)
async def _tenant_not_found(_: Request, exc: TenantNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TenantNameConflictError)
async def _tenant_name_conflict(_: Request, exc: TenantNameConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(TenantSlugConflictError)
async def _tenant_slug_conflict(_: Request, exc: TenantSlugConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidTenantTransitionError)
async def _invalid_transition(_: Request, exc: InvalidTenantTransitionError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(TenantLockedError)
async def _tenant_locked(_: Request, exc: TenantLockedError) -> JSONResponse:
    return JSONResponse(status_code=423, content={"detail": str(exc)})


@app.exception_handler(TenantOwnerRequiredError)
async def _owner_required(_: Request, exc: TenantOwnerRequiredError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(TenantContactConflictError)
async def _contact_conflict(_: Request, exc: TenantContactConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(TenantContactNotFoundError)
async def _contact_not_found(_: Request, exc: TenantContactNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})
