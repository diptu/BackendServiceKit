"""OrganizationSettingsHistoryRepository — append-only settings version history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.organization_settings_history import OrganizationSettingsHistory
from app.repositories.base import BaseRepository, PageResult


class OrganizationSettingsHistoryRepository(
    BaseRepository[OrganizationSettingsHistory]
):
    async def create(
        self, entry: OrganizationSettingsHistory
    ) -> OrganizationSettingsHistory:
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def latest_version(self, organization_id: UUID) -> int:
        result = await self._session.scalar(
            select(func.max(OrganizationSettingsHistory.version)).where(
                OrganizationSettingsHistory.organization_id == organization_id
            )
        )
        return result or 0

    async def list_for_organization(
        self, organization_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> PageResult[OrganizationSettingsHistory]:
        total_result = await self._session.scalar(
            select(func.count(OrganizationSettingsHistory.id)).where(
                OrganizationSettingsHistory.organization_id == organization_id
            )
        )
        total = total_result or 0

        rows = list(
            (
                await self._session.execute(
                    select(OrganizationSettingsHistory)
                    .where(
                        OrganizationSettingsHistory.organization_id == organization_id
                    )
                    .order_by(OrganizationSettingsHistory.version.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).scalars()
        )

        return PageResult(
            items=rows,
            total=total,
            has_more=(offset + len(rows)) < total,
            next_cursor=None,
        )
