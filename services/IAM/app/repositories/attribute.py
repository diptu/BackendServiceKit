"""AttributeRepository — user-scoped ABAC key/value attribute CRUD."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.attribute import Attribute
from app.repositories.base import BaseRepository


class AttributeRepository(BaseRepository[Attribute]):
    async def create(self, attribute: Attribute) -> Attribute:
        self._session.add(attribute)
        await self._session.flush()
        await self._session.refresh(attribute)
        return attribute

    async def save(self, attribute: Attribute) -> Attribute:
        self._session.add(attribute)
        await self._session.flush()
        await self._session.refresh(attribute)
        return attribute

    async def delete(self, attribute: Attribute) -> None:
        await self._session.delete(attribute)
        await self._session.flush()

    async def get_by_id(
        self,
        attribute_id: UUID,
        *,
        tenant_id: UUID,
        user_id: UUID | None = None,
    ) -> Attribute | None:
        stmt = select(Attribute).where(
            Attribute.id == attribute_id, Attribute.tenant_id == tenant_id
        )
        if user_id is not None:
            stmt = stmt.where(Attribute.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_key(self, tenant_id: UUID, user_id: UUID, key: str) -> bool:
        result = await self._session.scalar(
            select(func.count(Attribute.id))
            .where(Attribute.tenant_id == tenant_id)
            .where(Attribute.user_id == user_id)
            .where(Attribute.key == key)
        )
        return (result or 0) > 0

    async def list_for_user(self, tenant_id: UUID, user_id: UUID) -> list[Attribute]:
        result = await self._session.execute(
            select(Attribute)
            .where(Attribute.tenant_id == tenant_id, Attribute.user_id == user_id)
            .order_by(Attribute.key)
        )
        return list(result.scalars())
