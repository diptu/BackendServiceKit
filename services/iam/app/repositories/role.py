from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.models.role import Role


class RoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_name(
        self, name: str, *, organization_id: UUID | None = None
    ) -> Role | None:
        result = await self.db.execute(
            select(Role).where(
                Role.name == name, Role.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(
        self, slug: str, *, organization_id: UUID | None = None
    ) -> Role | None:
        """
        Look up a role by slug within a scope.

        organization_id=None (the default) matches global/platform roles —
        this preserves the existing registration/OAuth call sites, which
        only ever look up global roles like "guest".
        """
        result = await self.db.execute(
            select(Role).where(
                Role.slug == slug, Role.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, role_id: UUID) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def list_roles(
        self, *, organization_id: UUID | None = None, include_global: bool = True
    ) -> list[Role]:
        """
        List roles visible in a scope.

        organization_id=None + include_global=True -> only global roles.
        organization_id=<id> + include_global=True  -> that org's custom
        roles plus all global roles (so org_owner/org_admin/org_member are
        always assignable).
        """
        if organization_id is None:
            stmt = select(Role).where(Role.organization_id.is_(None))
        elif include_global:
            stmt = select(Role).where(
                (Role.organization_id == organization_id)
                | (Role.organization_id.is_(None))
            )
        else:
            stmt = select(Role).where(Role.organization_id == organization_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_by_slugs(self, slugs: list[str]) -> list[Permission]:
        if not slugs:
            return []
        result = await self.db.execute(
            select(Permission).where(Permission.slug.in_(slugs))
        )
        return list(result.scalars().all())

    async def create(self, role: Role) -> Role:
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def save(self, role: Role) -> Role:
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete(self, role: Role) -> None:
        await self.db.delete(role)
        await self.db.commit()
