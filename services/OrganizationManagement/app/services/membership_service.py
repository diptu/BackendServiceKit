"""MembershipService — organization<->user membership CRUD + audit trail."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import AddMemberCmd
from app.domain.enums import MembershipStatus
from app.domain.events import MemberAdded, MemberRemoved, MemberRoleChanged
from app.domain.exceptions import MembershipAlreadyExistsError, MembershipNotFoundError
from app.models.organization_membership import OrganizationMembership
from app.repositories.base import PageResult
from app.repositories.organization_event import OrganizationEventRepository
from app.repositories.organization_membership import OrganizationMembershipRepository


class MembershipService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OrganizationMembershipRepository(session)
        self._events_repo = OrganizationEventRepository(session)

    async def add_member(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID, cmd: AddMemberCmd
    ) -> OrganizationMembership:
        if await self._repo.get_by_user(organization_id, cmd.user_id) is not None:
            raise MembershipAlreadyExistsError(organization_id, cmd.user_id)

        membership = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=organization_id,
            tenant_id=tenant_id,
            user_id=cmd.user_id,
            role=cmd.role,
            status=MembershipStatus.ACTIVE,
            invited_by=cmd.added_by,
        )
        await self._repo.create(membership)

        await self._events_repo.record(
            organization_id,
            tenant_id,
            MemberAdded(
                organization_id=organization_id,
                user_id=cmd.user_id,
                role=cmd.role,
                added_by=cmd.added_by,
            ),
            performed_by=cmd.added_by,
        )
        return membership

    async def update_role(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        *,
        changed_by: uuid.UUID | None = None,
    ) -> OrganizationMembership:
        membership = await self._repo.get_by_user(organization_id, user_id)
        if membership is None:
            raise MembershipNotFoundError(organization_id, user_id)

        membership.role = role
        saved = await self._repo.save(membership)

        await self._events_repo.record(
            organization_id,
            tenant_id,
            MemberRoleChanged(
                organization_id=organization_id,
                user_id=user_id,
                new_role=role,
                changed_by=changed_by,
            ),
            performed_by=changed_by,
        )
        return saved

    async def remove_member(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        removed_by: uuid.UUID | None = None,
    ) -> None:
        membership = await self._repo.get_by_user(organization_id, user_id)
        if membership is None:
            raise MembershipNotFoundError(organization_id, user_id)

        await self._repo.delete(membership)

        await self._events_repo.record(
            organization_id,
            tenant_id,
            MemberRemoved(
                organization_id=organization_id, user_id=user_id, removed_by=removed_by
            ),
            performed_by=removed_by,
        )

    async def list_members(
        self, organization_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> PageResult[OrganizationMembership]:
        return await self._repo.list_for_organization(
            organization_id, cursor=cursor, limit=limit
        )

    async def count(self, organization_id: uuid.UUID) -> int:
        return await self._repo.count(organization_id)
