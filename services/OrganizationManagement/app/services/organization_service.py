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
from app.domain.events import (
    OrganizationCreated,
    OrganizationDeleted,
    OrganizationSettingsUpdated,
    OrganizationUpdated,
)
from app.domain.exceptions import (
    OrganizationDeletedError,
    OrganizationNotFoundError,
    OrganizationSlugConflictError,
)
from app.infrastructure.clients.tenent_client import TenentClient
from app.models.organization import Organization
from app.models.organization_event import OrganizationEvent
from app.models.organization_membership import OrganizationMembership
from app.models.organization_settings import OrganizationSettings
from app.models.organization_settings_history import OrganizationSettingsHistory
from app.models.organization_team import OrganizationTeam
from app.repositories.base import PageResult
from app.repositories.organization import OrganizationFilter, OrganizationRepository
from app.repositories.organization_event import OrganizationEventRepository
from app.repositories.organization_settings import OrganizationSettingsRepository
from app.repositories.organization_settings_history import (
    OrganizationSettingsHistoryRepository,
)
from app.services.membership_service import MembershipService
from app.services.team_service import TeamService


class OrganizationService:
    def __init__(
        self, session: AsyncSession, tenent_client: TenentClient | None = None
    ) -> None:
        self._session = session
        self._org_repo = OrganizationRepository(session)
        self._settings_repo = OrganizationSettingsRepository(session)
        self._settings_history_repo = OrganizationSettingsHistoryRepository(session)
        self._events_repo = OrganizationEventRepository(session)
        self._tenent = tenent_client or TenentClient()
        self._membership_svc = MembershipService(session)
        self._team_svc = TeamService(session)

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

        await self._events_repo.record(
            organization_id,
            cmd.tenant_id,
            OrganizationCreated(
                organization_id=organization_id,
                tenant_id=cmd.tenant_id,
                name=cmd.name,
                slug=cmd.slug,
            ),
        )

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

        changed_fields: list[str] = []
        if cmd.name is not None:
            organization.name = cmd.name
            changed_fields.append("name")
        if cmd.description is not None:
            organization.description = cmd.description
            changed_fields.append("description")

        saved = await self._org_repo.save(organization)

        if changed_fields:
            await self._events_repo.record(
                organization_id,
                tenant_id,
                OrganizationUpdated(
                    organization_id=organization_id, changed_fields=changed_fields
                ),
            )

        return saved

    async def delete(self, organization_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        organization = await self.get(organization_id, tenant_id)
        if organization.deleted_at is not None:
            return
        await self._org_repo.soft_delete(organization)
        await self._events_repo.record(
            organization_id,
            tenant_id,
            OrganizationDeleted(organization_id=organization_id),
        )

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
        *,
        changed_by: uuid.UUID | None = None,
    ) -> OrganizationSettings:
        await self.get(organization_id, tenant_id)
        org_settings = await self._settings_repo.get_by_organization_id(organization_id)
        if org_settings is None:
            org_settings = OrganizationSettings(
                id=uuid.uuid4(), organization_id=organization_id
            )

        changed_fields: list[str] = []
        if cmd.timezone is not None:
            org_settings.timezone = cmd.timezone
            changed_fields.append("timezone")
        if cmd.locale is not None:
            org_settings.locale = cmd.locale
            changed_fields.append("locale")
        if cmd.default_member_role is not None:
            org_settings.default_member_role = cmd.default_member_role
            changed_fields.append("default_member_role")
        if cmd.feature_flags is not None:
            org_settings.feature_flags = cmd.feature_flags
            changed_fields.append("feature_flags")
        if cmd.compliance_rules is not None:
            org_settings.compliance_rules = cmd.compliance_rules
            changed_fields.append("compliance_rules")

        saved = await self._settings_repo.save(org_settings)

        if changed_fields:
            next_version = (
                await self._settings_history_repo.latest_version(organization_id)
            ) + 1
            await self._settings_history_repo.create(
                OrganizationSettingsHistory(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    version=next_version,
                    snapshot={
                        "timezone": saved.timezone,
                        "locale": saved.locale,
                        "default_member_role": saved.default_member_role,
                        "feature_flags": saved.feature_flags,
                        "compliance_rules": saved.compliance_rules,
                    },
                    changed_by=changed_by,
                )
            )
            await self._events_repo.record(
                organization_id,
                tenant_id,
                OrganizationSettingsUpdated(
                    organization_id=organization_id,
                    changed_fields=changed_fields,
                    version=next_version,
                ),
                performed_by=changed_by,
            )

        return saved

    async def list_settings_history(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> PageResult[OrganizationSettingsHistory]:
        await self.get(organization_id, tenant_id)
        return await self._settings_history_repo.list_for_organization(
            organization_id, limit=limit, offset=offset
        )

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    async def list_events(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationEvent]:
        await self.get(organization_id, tenant_id)
        return await self._events_repo.list_by_organization(
            organization_id, cursor=cursor, limit=limit
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        organization = await self.get(organization_id, tenant_id)
        member_count = await self._membership_svc.count(organization_id)
        team_count = await self._team_svc.count(organization_id)
        return {
            "organization_id": organization.id,
            "status": organization.status,
            "created_at": organization.created_at,
            "member_count": member_count,
            # Workspace/Group have no owning service yet (Implementation-order.md
            # lists them after Organization) — honest 0 rather than a fabricated
            # number, same restraint this project applies elsewhere.
            "workspace_count": 0,
            "team_count": team_count,
            "group_count": 0,
        }

    # ------------------------------------------------------------------
    # Sub-resource enumeration
    # ------------------------------------------------------------------

    async def list_members(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationMembership]:
        await self.get(organization_id, tenant_id)
        return await self._membership_svc.list_members(
            organization_id, cursor=cursor, limit=limit
        )

    async def list_workspaces(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        # Workspace Management doesn't exist anywhere in this repo yet
        # (still a README-only stub) — honest empty stub, unlike
        # members/teams which now have real owning storage in this service.
        await self.get(organization_id, tenant_id)
        return {"items": [], "total": 0}

    async def list_teams(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationTeam]:
        await self.get(organization_id, tenant_id)
        return await self._team_svc.list_teams(
            organization_id, cursor=cursor, limit=limit
        )

    async def list_groups(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, object]:
        # Deliberately left as a stub — "groups" here was always a
        # placeholder synonym for what a future Group Management service
        # will own; not building a second, competing membership concept
        # alongside organization_memberships/team_memberships.
        await self.get(organization_id, tenant_id)
        return {"items": [], "total": 0}
