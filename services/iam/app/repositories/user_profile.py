from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.UserProfile.user_profile import UserProfile


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: UUID,
        *,
        full_name: str | None = None,
        avatar_url: str | None = None,
        bio: str | None = None,
    ) -> UserProfile:
        profile = await self.get(user_id)
        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                full_name=full_name,
                avatar_url=avatar_url,
                bio=bio,
            )
            self.session.add(profile)
        else:
            if full_name is not None:
                profile.full_name = full_name
            if avatar_url is not None:
                profile.avatar_url = avatar_url
            if bio is not None:
                profile.bio = bio
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
