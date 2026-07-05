"""UserService — read-only access to the User Service projection.

No create/update/delete: writes to UserProjection only ever come from the
(deferred) user.created/updated/deleted event consumer, never this API.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import UserNotFoundError
from app.models.user_projection import UserProjection
from app.repositories.base import PageResult
from app.repositories.user_projection import (
    UserProjectionFilter,
    UserProjectionRepository,
)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserProjectionRepository(session)

    async def get(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> UserProjection:
        user = await self._repo.get_by_id(user_id, tenant_id=tenant_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[UserProjection]:
        filters = UserProjectionFilter(tenant_id=tenant_id, search=search)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)
