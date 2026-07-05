"""FastAPI shared dependencies.

Every request is scoped to a tenant via the `X-Tenant-ID` header — see
README.md's API Reference: "All requests must include appropriate
multi-tenant routing identifiers (e.g., X-Tenant-ID header)". Organizations
are always looked up by (organization_id, tenant_id) together so a caller in
tenant A can never fetch, update, or delete an organization belonging to
tenant B, even by guessing its UUID.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.clients.tenent_client import TenentClient
from app.infrastructure.database.dependencies import get_db
from app.models.organization import Organization
from app.repositories.organization import OrganizationRepository
from app.services.invitation_service import InvitationService
from app.services.membership_service import MembershipService
from app.services.organization_service import OrganizationService
from app.services.team_service import TeamService


def get_tenent_client() -> TenentClient:
    return TenentClient()


async def get_organization_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenent_client: Annotated[TenentClient, Depends(get_tenent_client)],
) -> OrganizationService:
    return OrganizationService(db, tenent_client)


async def get_membership_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MembershipService:
    return MembershipService(db)


async def get_team_service(db: Annotated[AsyncSession, Depends(get_db)]) -> TeamService:
    return TeamService(db)


async def get_invitation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitationService:
    return InvitationService(db)


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


async def get_organization_or_404(
    organization_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
) -> Organization:
    repo = OrganizationRepository(db)
    organization = await repo.get_by_id(organization_id, tenant_id=tenant_id)
    if organization is None:
        raise HTTPException(
            status_code=404, detail=f"Organization {organization_id} not found."
        )
    return organization


DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
OrganizationDep = Annotated[Organization, Depends(get_organization_or_404)]
OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]
MembershipServiceDep = Annotated[MembershipService, Depends(get_membership_service)]
TeamServiceDep = Annotated[TeamService, Depends(get_team_service)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]
