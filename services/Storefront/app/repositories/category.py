"""Tenant-scoped data access for categories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    async def create(self, category: Category) -> Category:
        self._session.add(category)
        await self._session.flush()
        return category

    async def get_by_id(self, category_id: UUID, *, tenant_id: UUID) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id, Category.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, slug: str, *, tenant_id: UUID) -> bool:
        stmt = select(Category.id).where(
            Category.slug == slug, Category.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def list_all(self, *, tenant_id: UUID) -> list[Category]:
        stmt = (
            select(Category)
            .where(Category.tenant_id == tenant_id)
            .order_by(Category.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete(self, category: Category) -> None:
        await self._session.delete(category)
        await self._session.flush()
