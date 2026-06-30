"""Tenants CRUD + lifecycle + settings/owners/metadata sub-resources."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import DbDep, TenantDep
from app.domain.commands import (
    AddOwnerCmd,
    CreateTenantCmd,
    UpdateTenantCmd,
    UpdateTenantMetadataCmd,
    UpdateTenantSettingsCmd,
)
from app.domain.enums import TenantStatus
from app.domain.exceptions import (
    InvalidTenantTransitionError,
    TenantContactConflictError,
    TenantContactNotFoundError,
    TenantDeletedError,
    TenantNameConflictError,
    TenantNotFoundError,
    TenantOwnerRequiredError,
)
from app.repositories.tenant import TenantFilter
from app.schemas.tenant import (
    AddOwnerRequest,
    CreateTenantRequest,
    TenantListResponse,
    TenantMetadataEntry,
    TenantMetadataResponse,
    TenantOwnerListResponse,
    TenantOwnerResponse,
    TenantResponse,
    TenantSettingsResponse,
    TenantSummary,
    UpdateTenantMetadataRequest,
    UpdateTenantRequest,
    UpdateTenantSettingsRequest,
)
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def _svc(db: AsyncSession) -> TenantService:
    return TenantService(db)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(body: CreateTenantRequest, db: DbDep) -> TenantResponse:
    cmd = CreateTenantCmd(
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        region=body.region,
        timezone=body.timezone,
        locale=body.locale,
        currency=body.currency,
        owner_id=body.owner_id,
    )
    try:
        tenant = await _svc(db).create(cmd)
    except TenantNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantResponse.model_validate(tenant)


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    db: DbDep,
    status: TenantStatus | None = Query(None),
    region: str | None = Query(None),
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> TenantListResponse:
    filters = TenantFilter(status=status, region=region, search=search)
    page = await _svc(db).list(filters=filters, cursor=cursor, limit=limit)
    return TenantListResponse(
        items=[TenantSummary.model_validate(t) for t in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant: TenantDep) -> TenantResponse:
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant: TenantDep,
    body: UpdateTenantRequest,
    db: DbDep,
) -> TenantResponse:
    cmd = UpdateTenantCmd(
        display_name=body.display_name,
        description=body.description,
        timezone=body.timezone,
        locale=body.locale,
        currency=body.currency,
    )
    try:
        updated = await _svc(db).update(tenant.id, cmd)
    except TenantDeletedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TenantResponse.model_validate(updated)


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(tenant: TenantDep, db: DbDep) -> None:
    try:
        await _svc(db).delete(tenant.id)
    except InvalidTenantTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


@router.put("/{tenant_id}/provision", response_model=TenantResponse)
async def provision_tenant(tenant: TenantDep, db: DbDep) -> TenantResponse:
    try:
        updated = await _svc(db).provision(tenant.id)
    except InvalidTenantTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantResponse.model_validate(updated)


@router.put("/{tenant_id}/pend", response_model=TenantResponse)
async def pend_tenant(tenant: TenantDep, db: DbDep) -> TenantResponse:
    try:
        updated = await _svc(db).pend(tenant.id)
    except InvalidTenantTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantResponse.model_validate(updated)


@router.put("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(tenant: TenantDep, db: DbDep) -> TenantResponse:
    try:
        updated = await _svc(db).activate(tenant.id)
    except InvalidTenantTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantResponse.model_validate(updated)


@router.put("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(tenant: TenantDep, db: DbDep) -> TenantResponse:
    try:
        updated = await _svc(db).suspend(tenant.id)
    except InvalidTenantTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantResponse.model_validate(updated)


@router.put("/{tenant_id}/archive", response_model=TenantResponse)
async def archive_tenant(tenant: TenantDep, db: DbDep) -> TenantResponse:
    try:
        updated = await _svc(db).archive(tenant.id)
    except InvalidTenantTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/settings", response_model=TenantSettingsResponse)
async def get_settings(tenant: TenantDep, db: DbDep) -> TenantSettingsResponse:
    svc = _svc(db)
    s = await svc.get_settings(tenant.id)
    if s is None:
        raise HTTPException(status_code=404, detail="Settings not found.")
    return TenantSettingsResponse.model_validate(s)


@router.put("/{tenant_id}/settings", response_model=TenantSettingsResponse)
async def update_settings(
    tenant: TenantDep, body: UpdateTenantSettingsRequest, db: DbDep
) -> TenantSettingsResponse:
    cmd = UpdateTenantSettingsCmd(
        timezone=body.timezone,
        locale=body.locale,
        language=body.language,
        date_format=body.date_format,
        number_format=body.number_format,
        currency=body.currency,
        session_timeout_minutes=body.session_timeout_minutes,
        default_theme=body.default_theme,
    )
    s = await _svc(db).update_settings(tenant.id, cmd)
    return TenantSettingsResponse.model_validate(s)


# ---------------------------------------------------------------------------
# Owners / Contacts
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/owners", response_model=TenantOwnerListResponse)
async def list_owners(tenant: TenantDep, db: DbDep) -> TenantOwnerListResponse:
    contacts = await _svc(db).list_owners(tenant.id)
    return TenantOwnerListResponse(
        items=[TenantOwnerResponse.model_validate(c) for c in contacts],
        total=len(contacts),
    )


@router.post("/{tenant_id}/owners", response_model=TenantOwnerResponse, status_code=201)
async def add_owner(
    tenant: TenantDep, body: AddOwnerRequest, db: DbDep
) -> TenantOwnerResponse:
    cmd = AddOwnerCmd(user_id=body.user_id, role=body.role.value)
    try:
        contact = await _svc(db).add_owner(tenant.id, cmd)
    except TenantContactConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantOwnerResponse.model_validate(contact)


@router.delete("/{tenant_id}/owners/{contact_id}", status_code=204)
async def remove_owner(
    tenant: TenantDep, contact_id: UUID, db: DbDep
) -> None:
    try:
        await _svc(db).remove_owner(tenant.id, contact_id)
    except TenantContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TenantOwnerRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/metadata", response_model=TenantMetadataResponse)
async def get_metadata(tenant: TenantDep, db: DbDep) -> TenantMetadataResponse:
    entries = await _svc(db).get_metadata(tenant.id)
    return TenantMetadataResponse(
        tenant_id=tenant.id,
        entries=[TenantMetadataEntry(key=e.key, value=e.value) for e in entries],
        total=len(entries),
    )


@router.put("/{tenant_id}/metadata", response_model=TenantMetadataResponse)
async def update_metadata(
    tenant: TenantDep, body: UpdateTenantMetadataRequest, db: DbDep
) -> TenantMetadataResponse:
    cmd = UpdateTenantMetadataCmd(metadata=body.metadata)
    entries = await _svc(db).update_metadata(tenant.id, cmd)
    return TenantMetadataResponse(
        tenant_id=tenant.id,
        entries=[TenantMetadataEntry(key=e.key, value=e.value) for e in entries],
        total=len(entries),
    )
