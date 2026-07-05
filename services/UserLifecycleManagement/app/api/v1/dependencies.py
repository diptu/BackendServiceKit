"""FastAPI shared dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.clients.user_lifecycle_client import UserLifecycleClient
from app.infrastructure.database.dependencies import get_db
from app.services.lifecycle_service import LifecycleService


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


async def get_user_lifecycle_client() -> UserLifecycleClient:
    return UserLifecycleClient()


async def get_lifecycle_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    client: Annotated[UserLifecycleClient, Depends(get_user_lifecycle_client)],
) -> LifecycleService:
    return LifecycleService(db, client)


DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
LifecycleServiceDep = Annotated[LifecycleService, Depends(get_lifecycle_service)]
