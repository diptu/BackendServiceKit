from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import OrgRoleEnum
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role


class OrganizationRepository:
    """
    Data access for organizations and their memberships.

    Eager loading of members/user/role/permissions is handled declaratively
    via `lazy="selectin"` on the model relationships (see Organization,
    OrganizationMember, Role) — a plain `select(Organization)` already walks
    the whole graph in O(1) extra round trips, no N+1.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------
    # Organizations
    # -----------------------------------------------------------------

    async def create(self, organization: Organization) -> Organization:
        self.session.add(organization)
        await self.session.commit()
        return await self._reload(organization.id)

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        # populate_existing=True: re-populate relationships from the DB even
        # if this organization is already in the session's identity map with
        # a stale (e.g. pre-membership-write) `.members` collection cached.
        result = await self.session.execute(
            select(Organization)
            .where(Organization.id == organization_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Organization], int]:
        """Organizations the given user is an active member of."""
        base = (
            select(Organization)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
            )
        )
        return await self._paginate(base, page, page_size)

    async def list_all(
        self, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Organization], int]:
        return await self._paginate(select(Organization), page, page_size)

    async def save(self, organization: Organization) -> Organization:
        self.session.add(organization)
        await self.session.commit()
        return await self._reload(organization.id)

    async def delete(self, organization: Organization) -> None:
        await self.session.delete(organization)
        await self.session.commit()

    # -----------------------------------------------------------------
    # Membership
    # -----------------------------------------------------------------

    async def get_member(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMember | None:
        result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, organization_id: UUID) -> list[OrganizationMember]:
        result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    async def add_member(self, member: OrganizationMember) -> OrganizationMember:
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def save_member(self, member: OrganizationMember) -> OrganizationMember:
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove_member(self, member: OrganizationMember) -> None:
        await self.session.delete(member)
        await self.session.commit()

    async def count_members_with_role(self, role_id: UUID) -> int:
        """
        Count memberships currently holding `role_id`.

        Checked at the application layer (rather than relying on the DB's
        ON DELETE RESTRICT) so the guard behaves identically on SQLite
        tests and Postgres production.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(OrganizationMember)
            .where(OrganizationMember.role_id == role_id)
        )
        return result.scalar_one()

    async def count_active_owners(self, organization_id: UUID) -> int:
        """Count active members currently holding the global org_owner role."""
        result = await self.session.execute(
            select(func.count())
            .select_from(OrganizationMember)
            .join(Role, Role.id == OrganizationMember.role_id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_active.is_(True),
                Role.slug == OrgRoleEnum.OWNER.value,
            )
        )
        return result.scalar_one()

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    async def _reload(self, organization_id: UUID) -> Organization:
        organization = await self.get_by_id(organization_id)
        if organization is None:  # pragma: no cover — defensive, can't happen
            msg = f"Organization {organization_id} not found after write"
            raise RuntimeError(msg)
        return organization

    async def _paginate(
        self, base: Select[tuple[Organization]], page: int, page_size: int
    ) -> tuple[list[Organization], int]:
        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        rows = (
            (await self.session.execute(base.offset(offset).limit(page_size)))
            .scalars()
            .all()
        )
        return list(rows), total
