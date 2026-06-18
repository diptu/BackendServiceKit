from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.repositories.user import UserRepository
from app.repositories.user_profile import UserProfileRepository
from app.schemas.user import UserOut
from app.schemas.user_management import (
    AdminUserUpdate,
    ProfileUpdateRequest,
    UserListParams,
    UserPageResponse,
)
from app.schemas.userProfile.user_profile import UserProfileOut


class UserManagementService:
    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: UserProfileRepository,
    ) -> None:
        self._users = user_repo
        self._profiles = profile_repo

    async def list_users(self, params: UserListParams) -> UserPageResponse:
        users, total = await self._users.list_users(
            q=params.q,
            role=params.role,
            is_active=params.is_active,
            is_verified=params.is_verified,
            page=params.page,
            page_size=params.page_size,
        )
        items = [UserOut.model_validate(u) for u in users]
        return UserPageResponse.build(items, total, params.page, params.page_size)

    async def get_user(self, user_id: UUID) -> UserOut:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        return UserOut.model_validate(user)

    async def update_user(self, user_id: UUID, data: AdminUserUpdate) -> UserOut:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.is_verified is not None:
            user.is_verified = data.is_verified
        user = await self._users.save(user)
        return UserOut.model_validate(user)

    async def set_active(self, user_id: UUID, *, active: bool) -> UserOut:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        user.is_active = active
        user = await self._users.save(user)
        return UserOut.model_validate(user)

    async def get_profile(self, user_id: UUID) -> UserProfileOut:
        await self._assert_user_exists(user_id)
        profile = await self._profiles.get(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found."
            )
        return UserProfileOut.model_validate(profile)

    async def upsert_profile(
        self, user_id: UUID, data: ProfileUpdateRequest
    ) -> UserProfileOut:
        await self._assert_user_exists(user_id)
        profile = await self._profiles.upsert(
            user_id,
            full_name=data.full_name,
            avatar_url=data.avatar_url,
            bio=data.bio,
        )
        return UserProfileOut.model_validate(profile)

    async def _assert_user_exists(self, user_id: UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
