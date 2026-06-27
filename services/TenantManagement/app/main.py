"""FastAPI application factory for the Tenant Management Service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.openapi import TAGS_METADATA

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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
