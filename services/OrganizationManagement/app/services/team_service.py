"""TeamService — Team/Department CRUD + team<->user membership + audit trail."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateTeamCmd, UpdateTeamCmd
from app.domain.enums import TeamStatus
from app.domain.events import (
    TeamCreated,
    TeamDeleted,
    TeamMemberAdded,
    TeamMemberRemoved,
    TeamUpdated,
)
from app.domain.exceptions import (
    InvalidParentTeamError,
    TeamMembershipAlreadyExistsError,
    TeamMembershipNotFoundError,
    TeamNameConflictError,
    TeamNotFoundError,
)
from app.models.organization_team import OrganizationTeam
from app.repositories.base import PageResult
from app.repositories.organization_event import OrganizationEventRepository
from app.repositories.organization_team import OrganizationTeamRepository, TeamFilter


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OrganizationTeamRepository(session)
        self._events_repo = OrganizationEventRepository(session)

    async def create_team(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID, cmd: CreateTeamCmd
    ) -> OrganizationTeam:
        if await self._repo.exists_by_name(organization_id, cmd.name):
            raise TeamNameConflictError(organization_id, cmd.name)

        if cmd.parent_team_id is not None:
            parent = await self._repo.get_by_id(
                cmd.parent_team_id, organization_id=organization_id
            )
            if parent is None:
                raise InvalidParentTeamError(cmd.parent_team_id, organization_id)

        team_id = uuid.uuid4()
        team = OrganizationTeam(
            id=team_id,
            organization_id=organization_id,
            tenant_id=tenant_id,
            name=cmd.name,
            description=cmd.description,
            team_type=cmd.team_type,
            parent_team_id=cmd.parent_team_id,
            status=TeamStatus.ACTIVE,
        )
        await self._repo.create(team)

        await self._events_repo.record(
            organization_id,
            tenant_id,
            TeamCreated(
                organization_id=organization_id,
                team_id=team_id,
                name=cmd.name,
                team_type=cmd.team_type,
            ),
        )
        return team

    async def get(
        self, organization_id: uuid.UUID, team_id: uuid.UUID
    ) -> OrganizationTeam:
        team = await self._repo.get_by_id(team_id, organization_id=organization_id)
        if team is None:
            raise TeamNotFoundError(team_id)
        return team

    async def update_team(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        team_id: uuid.UUID,
        cmd: UpdateTeamCmd,
    ) -> OrganizationTeam:
        team = await self.get(organization_id, team_id)

        changed_fields: list[str] = []
        if cmd.name is not None and cmd.name != team.name:
            if await self._repo.exists_by_name(organization_id, cmd.name):
                raise TeamNameConflictError(organization_id, cmd.name)
            team.name = cmd.name
            changed_fields.append("name")
        if cmd.description is not None:
            team.description = cmd.description
            changed_fields.append("description")

        saved = await self._repo.save(team)

        if changed_fields:
            await self._events_repo.record(
                organization_id,
                tenant_id,
                TeamUpdated(team_id=team_id, changed_fields=changed_fields),
            )
        return saved

    async def delete_team(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID, team_id: uuid.UUID
    ) -> None:
        team = await self.get(organization_id, team_id)
        if team.deleted_at is not None:
            return
        await self._repo.soft_delete(team)
        await self._events_repo.record(
            organization_id, tenant_id, TeamDeleted(team_id=team_id)
        )

    async def list_teams(
        self, organization_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> PageResult[OrganizationTeam]:
        filters = TeamFilter(organization_id=organization_id)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def count(self, organization_id: uuid.UUID) -> int:
        filters = TeamFilter(organization_id=organization_id)
        return await self._repo.count(filters)

    # ------------------------------------------------------------------
    # Team <-> User membership
    # ------------------------------------------------------------------

    async def add_team_member(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self.get(organization_id, team_id)
        if await self._repo.has_member(team_id, user_id):
            raise TeamMembershipAlreadyExistsError(team_id, user_id)
        await self._repo.add_member(team_id, user_id)
        await self._events_repo.record(
            organization_id,
            tenant_id,
            TeamMemberAdded(team_id=team_id, user_id=user_id),
        )

    async def remove_team_member(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self.get(organization_id, team_id)
        if not await self._repo.has_member(team_id, user_id):
            raise TeamMembershipNotFoundError(team_id, user_id)
        await self._repo.remove_member(team_id, user_id)
        await self._events_repo.record(
            organization_id,
            tenant_id,
            TeamMemberRemoved(team_id=team_id, user_id=user_id),
        )

    async def list_team_members(
        self, organization_id: uuid.UUID, team_id: uuid.UUID
    ) -> list[uuid.UUID]:
        await self.get(organization_id, team_id)
        return await self._repo.list_members(team_id)
