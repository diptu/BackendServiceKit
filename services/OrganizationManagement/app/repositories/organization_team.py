"""OrganizationTeamRepository — Team/Department CRUD + team<->user membership."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, delete, func, or_, select

from app.domain.enums import TeamStatus
from app.models.organization_team import OrganizationTeam, TeamMembership
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class TeamFilter:
    organization_id: UUID
    team_type: str | None = field(default=None)


class OrganizationTeamRepository(BaseRepository[OrganizationTeam]):
    async def create(self, team: OrganizationTeam) -> OrganizationTeam:
        self._session.add(team)
        await self._session.flush()
        await self._session.refresh(team)
        return team

    async def save(self, team: OrganizationTeam) -> OrganizationTeam:
        self._session.add(team)
        await self._session.flush()
        await self._session.refresh(team)
        return team

    async def soft_delete(self, team: OrganizationTeam) -> None:
        team.deleted_at = datetime.now(timezone.utc)
        team.status = TeamStatus.DELETED
        self._session.add(team)
        await self._session.flush()

    async def get_by_id(
        self,
        team_id: UUID,
        *,
        organization_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> OrganizationTeam | None:
        stmt = select(OrganizationTeam).where(OrganizationTeam.id == team_id)
        if organization_id is not None:
            stmt = stmt.where(OrganizationTeam.organization_id == organization_id)
        if not include_deleted:
            stmt = stmt.where(OrganizationTeam.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, organization_id: UUID, name: str) -> bool:
        result = await self._session.scalar(
            select(func.count(OrganizationTeam.id))
            .where(OrganizationTeam.organization_id == organization_id)
            .where(OrganizationTeam.name == name)
            .where(OrganizationTeam.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: TeamFilter) -> int:
        stmt: Select[tuple[int]] = select(func.count(OrganizationTeam.id)).where(
            OrganizationTeam.organization_id == filters.organization_id,
            OrganizationTeam.deleted_at.is_(None),
        )
        if filters.team_type is not None:
            stmt = stmt.where(OrganizationTeam.team_type == filters.team_type)
        result = await self._session.scalar(stmt)
        return result or 0

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[OrganizationTeam]], filters: TeamFilter
    ) -> Select[tuple[OrganizationTeam]]:
        if filters.team_type is not None:
            stmt = stmt.where(OrganizationTeam.team_type == filters.team_type)
        return stmt

    # ------------------------------------------------------------------
    # Team <-> User membership
    # ------------------------------------------------------------------

    async def has_member(self, team_id: UUID, user_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(TeamMembership)
            .where(TeamMembership.team_id == team_id, TeamMembership.user_id == user_id)
        )
        return (result or 0) > 0

    async def add_member(self, team_id: UUID, user_id: UUID) -> None:
        self._session.add(TeamMembership(team_id=team_id, user_id=user_id))
        await self._session.flush()

    async def remove_member(self, team_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(TeamMembership).where(
                TeamMembership.team_id == team_id, TeamMembership.user_id == user_id
            )
        )
        await self._session.flush()

    async def list_members(self, team_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(TeamMembership.user_id)
            .where(TeamMembership.team_id == team_id)
            .order_by(TeamMembership.created_at.desc())
        )
        return list(result.scalars())

    # ------------------------------------------------------------------
    # Paginated listing — defined last: a method literally named `list`
    # shadows the builtin `list` type for annotations later in this same
    # class body (see IAM's RoleRepository for the same mypy quirk).
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        filters: TeamFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationTeam]:
        total = await self.count(filters)

        stmt: Select[tuple[OrganizationTeam]] = select(OrganizationTeam).where(
            OrganizationTeam.organization_id == filters.organization_id,
            OrganizationTeam.deleted_at.is_(None),
        )
        stmt = self._apply_filters(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    OrganizationTeam.created_at < cursor_dt,
                    and_(
                        OrganizationTeam.created_at == cursor_dt,
                        OrganizationTeam.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            OrganizationTeam.created_at.desc(), OrganizationTeam.id.desc()
        ).limit(limit + 1)

        rows = list((await self._session.execute(stmt)).scalars())
        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor
        )
