"""AvatarService — set/get/delete a URL reference to an already-uploaded image."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import SetAvatarCmd
from app.infrastructure.clients.user_profile_client import UserProfileClient
from app.models.avatar import Avatar
from app.repositories.avatar import AvatarRepository


class AvatarService:
    def __init__(
        self,
        session: AsyncSession,
        client: UserProfileClient | None = None,
    ) -> None:
        self._session = session
        self._repo = AvatarRepository(session)
        self._client = client or UserProfileClient()

    async def get_avatar(self, user_id: UUID) -> Avatar | None:
        return await self._repo.get_by_user_id(user_id)

    async def set_avatar(
        self, user_id: UUID, tenant_id: UUID, cmd: SetAvatarCmd
    ) -> Avatar:
        avatar = await self._repo.get_by_user_id(user_id)
        if avatar is None:
            await self._client.assert_user_exists(user_id, tenant_id)
            avatar = Avatar(user_id=user_id, tenant_id=tenant_id, url=cmd.url)
        else:
            avatar.url = cmd.url
        avatar.content_type = cmd.content_type
        return await self._repo.save(avatar)

    async def delete_avatar(self, user_id: UUID) -> None:
        avatar = await self._repo.get_by_user_id(user_id)
        if avatar is not None:
            await self._repo.delete(avatar)
