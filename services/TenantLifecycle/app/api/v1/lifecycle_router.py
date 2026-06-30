"""Tenant lifecycle transition endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.openapi import RESPONSES_READ, RESPONSES_TRANSITION
from app.infrastructure.database.dependencies import get_db
from app.schemas.lifecycle import (
    LifecycleEventResponse,
    LifecycleHistoryResponse,
    LifecycleStateResponse,
    TransitionRequest,
)
from app.services.lifecycle_service import TenantLifecycleService

router = APIRouter(prefix="/tenant-lifecycle", tags=["Lifecycle"])


# ---------------------------------------------------------------------------
# Lifecycle transition endpoints
# ---------------------------------------------------------------------------


@router.put(
    "/{tenant_id}/provisioning",
    response_model=LifecycleStateResponse,
    summary="Start tenant provisioning",
    description="""\
Register a tenant with the Lifecycle Service and start provisioning.

**Valid source state:** none (tenant must not yet be registered with TL)

This is the **entry point** into the TL state machine. It creates the initial
`provisioning` lifecycle record and calls TenantManagement's `POST /provision`
to advance TM from `draft → provisioning`.

This endpoint is **idempotent** — calling it when the tenant is already
`provisioning` returns `200 OK` with the current state and emits no duplicate event.

Emits a `TenantProvisioningStarted` domain event.

Returns `409 Conflict` if the tenant is already in any other state.
""",
    responses=RESPONSES_TRANSITION,
)
async def provision_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).provision(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/pending",
    response_model=LifecycleStateResponse,
    summary="Mark tenant as pending",
    description="""\
Transition a tenant from `provisioning` to `pending` state.

**Valid source state:** `provisioning`

`pending` is the mandatory compliance gate between infrastructure provisioning and
full activation. Called once async infra setup is complete but before the tenant
goes live.

This endpoint is **idempotent** — calling it on an already-`pending` tenant
returns `200 OK` with the current state and emits no duplicate event.

Emits a `TenantPended` domain event on the first transition only.

Returns `404 Not Found` if the tenant is not registered with TL.
Returns `409 Conflict` for all other source states (active, suspended, locked, archived, deleted).
""",
    responses=RESPONSES_TRANSITION,
)
async def pend_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).pend(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/activate",
    response_model=LifecycleStateResponse,
    summary="Activate tenant",
    description="""\
Transition a tenant from `pending` to `active` state.

**Valid source state:** `pending`

This endpoint is **idempotent** — calling it on an already-`active` tenant
returns `200 OK` with the current state and emits no duplicate event.

Callers must invoke `PUT /pending` first to advance through `provisioning → pending`.

Emits a `TenantActivated` domain event on the first activation only.

Returns `404 Not Found` if the tenant is not registered with TL.
Returns `409 Conflict` for all other source states (provisioning, suspended, locked, archived, deleted).
""",
    responses=RESPONSES_TRANSITION,
)
async def activate_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).activate(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/suspend",
    response_model=LifecycleStateResponse,
    summary="Suspend tenant (idempotent)",
    description="""\
Transition an `active` tenant to `suspended` state.

**Valid source state:** `active`

This endpoint is **idempotent** — calling it on an already-`suspended` tenant
returns `200 OK` with the current state and emits no duplicate event.

**Effects:**
- All user logins for the tenant are blocked.
- All API access for the tenant is blocked.
- Tenant data is preserved.

Emits a `TenantSuspended` domain event on first suspension only.

Returns `409 Conflict` for all other source states (provisioning, locked, archived, deleted).
""",
    responses=RESPONSES_TRANSITION,
)
async def suspend_tenant_idempotent(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).suspend_idempotent(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)



@router.put(
    "/{tenant_id}/reactivate",
    response_model=LifecycleStateResponse,
    summary="Reactivate tenant",
    description="""\
Transition a `suspended` tenant back to `active` state.

**Valid source state:** `suspended`

Called by a platform administrator to restore access after suspension.
Emits a `TenantReactivated` domain event.

Returns `409 Conflict` if the tenant is not currently `suspended`.
""",
    responses=RESPONSES_TRANSITION,
)
async def reactivate_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).reactivate(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/lock",
    response_model=LifecycleStateResponse,
    summary="Lock tenant",
    description="""\
Transition an `active` tenant to `locked` state.

**Valid source state:** `active`

**Effects:**
- All write operations on the tenant are blocked.
- Read operations remain available.
- Typically used for compliance holds or security incidents.

Emits a `TenantLocked` domain event.

Returns `409 Conflict` if the tenant is not currently `active`.
""",
    responses=RESPONSES_TRANSITION,
)
async def lock_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).lock(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/unlock",
    response_model=LifecycleStateResponse,
    summary="Unlock tenant",
    description="""\
Transition a `locked` tenant back to `active` state (security incident resolved).

**Valid source state:** `locked`

Called by an administrator after investigation confirms the tenant is safe to resume.
Syncs TenantManagement from `suspended → active` (TM has no locked state; locking
is proxied as a suspension at the TM level).

Emits a `TenantUnlocked` domain event.

Returns `409 Conflict` if the tenant is not currently `locked`.
""",
    responses=RESPONSES_TRANSITION,
)
async def unlock_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).unlock(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/archive",
    response_model=LifecycleStateResponse,
    summary="Archive tenant",
    description="""\
Transition a tenant to `archived` (read-only) state.

**Valid source states:** `active`, `suspended`, `locked`

**Effects:**
- All write operations return `423 Locked`.
- Data is retained for compliance and audit.
- Archival is a prerequisite for deletion.

Emits a `TenantArchived` domain event.
""",
    responses=RESPONSES_TRANSITION,
)
async def archive_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).archive(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


@router.put(
    "/{tenant_id}/delete",
    response_model=LifecycleStateResponse,
    summary="Soft-delete tenant",
    description="""\
Transition an `archived` tenant to `deleted` state.

**Valid source state:** `archived`

The tenant record is soft-deleted. Hard deletion is handled by the Tenant
Offboarding Service. Emits a `TenantDeleted` domain event.

Returns `409 Conflict` if the tenant is not currently `archived`.
""",
    responses=RESPONSES_TRANSITION,
)
async def delete_tenant(
    tenant_id: UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> LifecycleStateResponse:
    state = await TenantLifecycleService(db).delete(
        tenant_id, reason=body.reason, performed_by=body.performed_by
    )
    return LifecycleStateResponse.model_validate(state)


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/{tenant_id}/history",
    response_model=LifecycleHistoryResponse,
    summary="Get lifecycle history",
    description="""\
Return the full audit log of lifecycle transitions for a tenant.

Results are ordered by `occurred_at` descending (newest first).
Supports **cursor-based pagination**: pass the `next_cursor` value from the
previous response as a query parameter to retrieve the next page.
""",
    responses=RESPONSES_READ,
)
async def get_lifecycle_history(
    tenant_id: UUID,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of events to return (1–100).",
    ),
    next_cursor: str | None = Query(
        default=None,
        description="Opaque cursor from the previous response. Omit for the first page.",
    ),
    db: AsyncSession = Depends(get_db),
) -> LifecycleHistoryResponse:
    result = await TenantLifecycleService(db).get_history(
        tenant_id, limit=limit, next_cursor=next_cursor
    )
    return LifecycleHistoryResponse(
        tenant_id=tenant_id,
        events=[LifecycleEventResponse.model_validate(e) for e in result.items],
        total=result.total,
        has_more=result.has_more,
        next_cursor=result.next_cursor,
    )
