"""FastAPI shared dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.clients.user_profile_client import UserProfileClient
from app.infrastructure.database.dependencies import get_db
from app.services.avatar_service import AvatarService
from app.services.profile_service import ProfileService


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


async def get_user_profile_client() -> UserProfileClient:
    return UserProfileClient()


async def get_profile_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    client: Annotated[UserProfileClient, Depends(get_user_profile_client)],
) -> ProfileService:
    return ProfileService(db, client)


async def get_avatar_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    client: Annotated[UserProfileClient, Depends(get_user_profile_client)],
) -> AvatarService:
    return AvatarService(db, client)


DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
AvatarServiceDep = Annotated[AvatarService, Depends(get_avatar_service)]
