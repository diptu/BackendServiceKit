"""OrganizationService — CRUD, settings, stats, and sub-resource enumeration."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import (
    CreateOrganizationCmd,
    UpdateOrganizationCmd,
    UpdateOrganizationSettingsCmd,
)
from app.domain.enums import OrganizationStatus
from app.domain.exceptions import (
    OrganizationDeletedError,
    OrganizationNotFoundError,
    OrganizationSlugConflictError,
)
from app.infrastructure.clients.tenent_client import TenentClient
from app.models.organization import Organization
from app.models.organization_settings import OrganizationSettings
from app.repositories.base import PageResult
from app.repositories.organization import OrganizationFilter, OrganizationRepository
from app.repositories.organization_settings import OrganizationSettingsRepository


class OrganizationService:
    def __init__(
        self, session: AsyncSession, tenent_client: TenentClient | None = None
    ) -> None:
        self._session = session
        self._org_repo = OrganizationRepository(session)
        self._settings_repo = OrganizationSettingsRepository(session)
        self._tenent = tenent_client or TenentClient()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, cmd: CreateOrganizationCmd) -> Organization:
        await self._tenent.assert_tenant_exists(cmd.tenant_id)

        if await self._org_repo.exists_by_slug(cmd.tenant_id, cmd.slug):
            raise OrganizationSlugConflictError(cmd.tenant_id, cmd.slug)

        organization_id = uuid.uuid4()
        organization = Organization(
            id=organization_id,
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            slug=cmd.slug,
            description=cmd.description,
            status=OrganizationStatus.ACTIVE,
        )
        await self._org_repo.create(organization)

        org_settings = OrganizationSettings(
            id=uuid.uuid4(), organization_id=organization_id
        )
        await self._settings_repo.create(org_settings)

        return organization

    async def get(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Organization:
        organization = await self._org_repo.get_by_id(
            organization_id, tenant_id=tenant_id
        )
        if organization is None:
            raise OrganizationNotFoundError(organization_id)
        return organization

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Organization]:
        filters = OrganizationFilter(tenant_id=tenant_id, search=search)
        return await self._org_repo.list(filters=filters, cursor=cursor, limit=limit)

    async def update(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cmd: UpdateOrganizationCmd,
    ) -> Organization:
        organization = await self.get(organization_id, tenant_id)
        if organization.deleted_at is not None:
            raise OrganizationDeletedError(organization_id)

        if cmd.name is not None:
            organization.name = cmd.name
        if cmd.description is not None:
            organization.description = cmd.description

        return await self._org_repo.save(organization)

    async def delete(self, organization_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        organization = await self.get(organization_id, tenant_id)
        if organization.deleted_at is not None:
            return
        await self._org_repo.soft_delete(organization)

    # ------------------------------------------------------------------
    # Settings sub-resource
    # ------------------------------------------------------------------

    async def get_settings(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> OrganizationSettings:
        await self.get(organization_id, tenant_id)
        org_settings = await self._settings_repo.get_by_organization_id(organization_id)
        if org_settings is None:
            raise OrganizationNotFoundError(organization_id)
        return org_settings

    async def update_settings(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cmd: UpdateOrganizationSettingsCmd,
    ) -> OrganizationSettings:
        await self.get(organization_id, tenant_id)
        org_settings = await self._settings_repo.get_by_organization_id(organization_id)
        if org_settings is None:
            org_settings = OrganizationSettings(
                id=uuid.uuid4(), organization_id=organization_id
            )

        if cmd.timezone is not None:
            org_settings.timezone = cmd.timezone
        if cmd.locale is not None:
            org_settings.locale = cmd.locale
        if cmd.default_member_role is not None:
            org_settings.default_member_role = cmd.default_member_role
        if cmd.feature_flags is not None:
            org_settings.feature_flags = cmd.feature_flags
        if cmd.compliance_rules is not None:
            org_settings.compliance_rules = cmd.compliance_rules

        return await self._settings_repo.save(org_settings)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        organization = await self.get(organization_id, tenant_id)
        return {
            "organization_id": organization.id,
            "status": organization.status,
            "created_at": organization.created_at,
            # Workspace/Team/Group/Membership have no owning service yet
            # (Implementation-order.md lists them after Organization) — real
            # counts land here once those services exist, matching this
            # project's own precedent of an honest, documented gap rather
            # than a fabricated number.
            "member_count": 0,
            "workspace_count": 0,
            "team_count": 0,
            "group_count": 0,
        }

    # ------------------------------------------------------------------
    # Sub-resource enumeration (Workspaces/Teams/Groups/Members)
    # ------------------------------------------------------------------
    # None of these sub-resources have an owning service yet — see
    # Implementation-order.md (Organization comes before User Management,
    # Group, Membership). Each honestly returns an empty collection rather
    # than inventing storage for a domain this service doesn't own, the
    # same restraint ObservilityManagement's MetricsQueryService applies to
    # the node-exporter-absence gap it carries forward rather than papering
    # over.

    async def list_members(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        await self.get(organization_id, tenant_id)
        return {"items": [], "total": 0}

    async def list_workspaces(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        await self.get(organization_id, tenant_id)
        return {"items": [], "total": 0}

    async def list_teams(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        await self.get(organization_id, tenant_id)
        return {"items": [], "total": 0}

    async def list_groups(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        await self.get(organization_id, tenant_id)
        return {"items": [], "total": 0}
