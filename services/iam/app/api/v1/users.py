from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_async_db, get_current_user, require_admin
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
from app.services.user_management import UserManagementService

router = APIRouter(prefix="/users", tags=["User Management"])


def _get_service(db: AsyncSession = Depends(get_async_db)) -> UserManagementService:
    return UserManagementService(
        user_repo=UserRepository(db),
        profile_repo=UserProfileRepository(db),
    )


# ---------------------------------------------------------------------------
# Self endpoints (any authenticated user)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserOut, summary="Get own user record")
async def get_me(
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    return current_user


# ---------------------------------------------------------------------------
# Admin — list / get / update users
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=UserPageResponse,
    summary="List users (admin)",
)
async def list_users(
    _admin: Annotated[UserOut, Depends(require_admin)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
    q: Annotated[str | None, Query(description="Search email or name")] = None,
    role: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    is_verified: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserPageResponse:
    params = UserListParams(
        q=q,
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        page=page,
        page_size=page_size,
    )
    return await svc.list_users(params)


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Get user by ID (admin or self)",
)
async def get_user(
    user_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
) -> UserOut:
    if current_user.id != user_id and not current_user.is_superuser:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return await svc.get_user(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    summary="Update user flags (admin)",
)
async def update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    _admin: Annotated[UserOut, Depends(require_admin)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
) -> UserOut:
    return await svc.update_user(user_id, data)


@router.post(
    "/{user_id}/activate",
    response_model=UserOut,
    summary="Activate a user (admin)",
)
async def activate_user(
    user_id: UUID,
    _admin: Annotated[UserOut, Depends(require_admin)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
) -> UserOut:
    return await svc.set_active(user_id, active=True)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserOut,
    summary="Deactivate a user (admin)",
)
async def deactivate_user(
    user_id: UUID,
    _admin: Annotated[UserOut, Depends(require_admin)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
) -> UserOut:
    return await svc.set_active(user_id, active=False)


# ---------------------------------------------------------------------------
# Profile sub-resource
# ---------------------------------------------------------------------------


@router.get(
    "/{user_id}/profile",
    response_model=UserProfileOut,
    summary="Get user profile (admin or self)",
)
async def get_profile(
    user_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
) -> UserProfileOut:
    if current_user.id != user_id and not current_user.is_superuser:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return await svc.get_profile(user_id)


@router.patch(
    "/{user_id}/profile",
    response_model=UserProfileOut,
    summary="Update user profile (admin or self)",
)
async def update_profile(
    user_id: UUID,
    data: ProfileUpdateRequest,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[UserManagementService, Depends(_get_service)],
) -> UserProfileOut:
    if current_user.id != user_id and not current_user.is_superuser:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return await svc.upsert_profile(user_id, data)
