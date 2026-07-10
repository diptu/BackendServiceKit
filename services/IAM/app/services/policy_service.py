"""PolicyService — AbacPolicy CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreatePolicyCmd, UpdatePolicyCmd
from app.domain.exceptions import PolicyNameConflictError, PolicyNotFoundError
from app.models.policy import AbacPolicy
from app.repositories.base import PageResult
from app.repositories.policy import PolicyFilter, PolicyRepository


class PolicyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PolicyRepository(session)

    async def create(self, cmd: CreatePolicyCmd) -> AbacPolicy:
        if await self._repo.exists_by_name(cmd.tenant_id, cmd.name):
            raise PolicyNameConflictError(cmd.tenant_id, cmd.name)

        policy = AbacPolicy(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            description=cmd.description,
            effect=cmd.effect,
            resource_type=cmd.resource_type,
            action=cmd.action,
            conditions=cmd.conditions,
            priority=cmd.priority,
            is_active=cmd.is_active,
        )
        return await self._repo.create(policy)

    async def get(self, policy_id: uuid.UUID, tenant_id: uuid.UUID) -> AbacPolicy:
        policy = await self._repo.get_by_id(policy_id, tenant_id=tenant_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AbacPolicy]:
        filters = PolicyFilter(tenant_id=tenant_id, search=search)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def update(
        self, policy_id: uuid.UUID, tenant_id: uuid.UUID, cmd: UpdatePolicyCmd
    ) -> AbacPolicy:
        policy = await self.get(policy_id, tenant_id)

        if cmd.name is not None and cmd.name != policy.name:
            if await self._repo.exists_by_name(tenant_id, cmd.name):
                raise PolicyNameConflictError(tenant_id, cmd.name)
            policy.name = cmd.name
        if cmd.description is not None:
            policy.description = cmd.description
        if cmd.effect is not None:
            policy.effect = cmd.effect
        if cmd.resource_type is not None:
            policy.resource_type = cmd.resource_type
        if cmd.action is not None:
            policy.action = cmd.action
        if cmd.conditions is not None:
            policy.conditions = cmd.conditions
        if cmd.priority is not None:
            policy.priority = cmd.priority
        if cmd.is_active is not None:
            policy.is_active = cmd.is_active

        return await self._repo.save(policy)

    async def delete(self, policy_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        policy = await self.get(policy_id, tenant_id)
        if policy.deleted_at is not None:
            return
        await self._repo.soft_delete(policy)
