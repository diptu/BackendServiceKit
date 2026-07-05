"""AttributeService — user-scoped ABAC attribute CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateAttributeCmd, UpdateAttributeCmd
from app.domain.exceptions import AttributeKeyConflictError, AttributeNotFoundError
from app.models.attribute import Attribute
from app.repositories.attribute import AttributeRepository


class AttributeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AttributeRepository(session)

    async def create(self, cmd: CreateAttributeCmd) -> Attribute:
        if await self._repo.exists_by_key(cmd.tenant_id, cmd.user_id, cmd.key):
            raise AttributeKeyConflictError(cmd.user_id, cmd.key)

        attribute = Attribute(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            user_id=cmd.user_id,
            key=cmd.key,
            value=cmd.value,
            value_type=cmd.value_type,
        )
        return await self._repo.create(attribute)

    async def get(
        self, attribute_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Attribute:
        attribute = await self._repo.get_by_id(
            attribute_id, tenant_id=tenant_id, user_id=user_id
        )
        if attribute is None:
            raise AttributeNotFoundError(attribute_id)
        return attribute

    async def list_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[Attribute]:
        return await self._repo.list_for_user(tenant_id, user_id)

    async def update(
        self,
        attribute_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cmd: UpdateAttributeCmd,
    ) -> Attribute:
        attribute = await self.get(attribute_id, user_id, tenant_id)

        if cmd.value is not None:
            attribute.value = cmd.value
        if cmd.value_type is not None:
            attribute.value_type = cmd.value_type

        return await self._repo.save(attribute)

    async def delete(
        self, attribute_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        attribute = await self.get(attribute_id, user_id, tenant_id)
        await self._repo.delete(attribute)
