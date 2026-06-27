"""Tenant resource endpoints — CRUD, lifecycle transitions, sub-resources."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.openapi import (
    RESPONSES_CREATE,
    RESPONSES_READ,
    RESPONSES_TRANSITION,
    RESPONSES_WRITE,
    R_401,
    R_403,
    R_404,
)
from app.infrastructure.database.dependencies import get_db
from app.schemas.tenant import (
    AddOwnerRequest,
    CreateTenantRequest,
    TenantListResponse,
    TenantMetadataResponse,
    TenantOwnerListResponse,
    TenantOwnerResponse,
    TenantResponse,
    TenantSettingsResponse,
    TransitionRequest,
    UpdateTenantMetadataRequest,
    UpdateTenantRequest,
    UpdateTenantSettingsRequest,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])

_TODO = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Not implemented yet.",
)

# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant",
    description="""\
Create a new tenant record in `draft` state.

The provisioning workflow is triggered automatically after creation, which
transitions the tenant through `provisioning` → `active`.

**Constraints:**
- `name` (slug) must be globally unique and URL-safe (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`).
- `name` is immutable after creation.
- Only platform administrators may create tenants.
""",
    responses=RESPONSES_CREATE,
)
async def create_tenant(
    body: CreateTenantRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raise _TODO


@router.get(
    "",
    response_model=TenantListResponse,
    summary="List tenants",
    description="""\
Return a cursor-paginated list of tenants.

Supports filtering by `status` and `region`. Soft-deleted tenants
(`status=deleted`) are excluded from results unless explicitly requested.

**Sorting:** `created_at` descending by default.
""",
    responses={401: R_401, 403: R_403},
)
async def list_tenants(
    cursor: str | None = Query(
        default=None,
        description="Opaque cursor from the previous response. Omit for the first page.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return (1–100).",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by tenant status (e.g. `active`, `suspended`).",
    ),
    region: str | None = Query(
        default=None,
        description="Filter by deployment region (e.g. `us-east-1`).",
    ),
    db: AsyncSession = Depends(get_db),
) -> TenantListResponse:
    raise _TODO


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant",
    description="Retrieve the full tenant record by UUID.",
    responses=RESPONSES_READ,
)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raise _TODO


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant",
    description="""\
Partially update mutable tenant fields.

**Immutable fields** (cannot be changed after creation):
- `id`
- `name` (slug)
- `created_at`

All other fields in the request body are optional — only provided fields are updated.
Every update emits a `TenantUpdated` domain event and generates an audit record.
""",
    responses=RESPONSES_WRITE,
)
async def update_tenant(
    tenant_id: UUID,
    body: UpdateTenantRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raise _TODO


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete tenant",
    description="""\
Soft-delete a tenant.

The tenant must be in `archived` state before deletion. The record is retained
for audit purposes and the `name` slug remains reserved until hard-deletion by the
Tenant Offboarding Service.

Emits a `TenantDeleted` domain event.

> **Note:** Hard deletion is handled by the Tenant Offboarding Service, not this endpoint.
""",
    responses={
        **RESPONSES_WRITE,
        409: {
            "description": (
                "Conflict — tenant must be in `archived` state before deletion. "
                "Transition to `archived` first."
            )
        },
    },
)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    raise _TODO


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


@router.post(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    tags=["Tenant Lifecycle"],
    summary="Activate or reactivate tenant",
    description="""\
Transition a tenant to `active` state.

**Valid source states:** `provisioning`, `suspended`

- `provisioning → active`: Called by the Provisioning Service on successful completion.
- `suspended → active`: Called by a platform administrator to reactivate a suspended tenant.

Emits `TenantActivated` or `TenantReactivated` event depending on the source state.

Returns `409 Conflict` for all other source states.
""",
    responses=RESPONSES_TRANSITION,
)
async def activate_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raise _TODO


@router.post(
    "/{tenant_id}/suspend",
    response_model=TenantResponse,
    tags=["Tenant Lifecycle"],
    summary="Suspend tenant",
    description="""\
Transition an `active` tenant to `suspended` state.

**Effects:**
- All user logins for the tenant are immediately blocked.
- All API access for the tenant is blocked.
- All tenant data is preserved.

Providing a `reason` is strongly recommended for audit clarity.
Emits a `TenantSuspended` event.

Returns `409 Conflict` if the tenant is not currently in `active` state.
""",
    responses=RESPONSES_TRANSITION,
)
async def suspend_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raise _TODO


@router.post(
    "/{tenant_id}/archive",
    response_model=TenantResponse,
    tags=["Tenant Lifecycle"],
    summary="Archive tenant",
    description="""\
Transition a tenant to `archived` (read-only) state.

**Valid source states:** `active`, `suspended`

**Effects:**
- All write operations on the tenant and its resources return `423 Locked`.
- The tenant is retained for compliance and audit purposes.
- Archival is a prerequisite for soft-deletion.

Emits a `TenantArchived` event.
""",
    responses=RESPONSES_TRANSITION,
)
async def archive_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raise _TODO


# ---------------------------------------------------------------------------
# Settings sub-resource
# ---------------------------------------------------------------------------


@router.get(
    "/{tenant_id}/settings",
    response_model=TenantSettingsResponse,
    tags=["Tenant Settings"],
    summary="Get tenant settings",
    description="Retrieve all configuration settings for a tenant.",
    responses=RESPONSES_READ,
)
async def get_settings(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsResponse:
    raise _TODO


@router.patch(
    "/{tenant_id}/settings",
    response_model=TenantSettingsResponse,
    tags=["Tenant Settings"],
    summary="Update tenant settings",
    description="""\
Partially update tenant configuration settings.

All fields are optional — only provided fields are updated.
Updates are versioned; all changes generate an audit record and emit a
`TenantConfigurationUpdated` event.

Returns `423 Locked` if the tenant is in `archived` state.
""",
    responses=RESPONSES_WRITE,
)
async def update_settings(
    tenant_id: UUID,
    body: UpdateTenantSettingsRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsResponse:
    raise _TODO


# ---------------------------------------------------------------------------
# Owners sub-resource
# ---------------------------------------------------------------------------


@router.get(
    "/{tenant_id}/owners",
    response_model=TenantOwnerListResponse,
    tags=["Tenant Owners"],
    summary="List tenant owners",
    description="Return all active owners and admins of the tenant.",
    responses=RESPONSES_READ,
)
async def list_owners(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantOwnerListResponse:
    raise _TODO


@router.post(
    "/{tenant_id}/owners",
    response_model=TenantOwnerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tenant Owners"],
    summary="Add tenant owner",
    description="""\
Add a user as an owner or admin of the tenant.

The `user_id` must be a valid user ID from the User Service.
Adding the same user twice returns `409 Conflict`.
Ownership changes are audited and emit a `TenantOwnerAdded` event.
""",
    responses={
        **RESPONSES_CREATE,
        409: {"description": "Conflict — this user is already an owner of the tenant."},
    },
)
async def add_owner(
    tenant_id: UUID,
    body: AddOwnerRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantOwnerResponse:
    raise _TODO


@router.delete(
    "/{tenant_id}/owners/{owner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tenant Owners"],
    summary="Remove tenant owner",
    description="""\
Remove a user from the tenant's owner list.

Returns `422 Unprocessable Entity` if the user being removed is the last active owner.
Every tenant must retain at least one active owner at all times.

Emits a `TenantOwnerRemoved` event.
""",
    responses={
        **RESPONSES_WRITE,
        422: {
            "description": (
                "Unprocessable Entity — cannot remove the last active owner. "
                "Add a replacement owner first."
            )
        },
    },
)
async def remove_owner(
    tenant_id: UUID,
    owner_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    raise _TODO


# ---------------------------------------------------------------------------
# Metadata sub-resource
# ---------------------------------------------------------------------------


@router.get(
    "/{tenant_id}/metadata",
    response_model=TenantMetadataResponse,
    tags=["Tenant Metadata"],
    summary="Get tenant metadata",
    description="Retrieve all key-value metadata entries for a tenant.",
    responses=RESPONSES_READ,
)
async def get_metadata(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantMetadataResponse:
    raise _TODO


@router.patch(
    "/{tenant_id}/metadata",
    response_model=TenantMetadataResponse,
    tags=["Tenant Metadata"],
    summary="Update tenant metadata",
    description="""\
Upsert metadata key-value pairs for a tenant.

**Behaviour:**
- Existing keys are **overwritten**.
- New keys are **added**.
- No keys are deleted by this operation. To clear a key, set its value to `""`.

Updates generate an audit record. No domain event is emitted for metadata changes.

Returns `423 Locked` if the tenant is in `archived` state.
""",
    responses=RESPONSES_WRITE,
)
async def update_metadata(
    tenant_id: UUID,
    body: UpdateTenantMetadataRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantMetadataResponse:
    raise _TODO
