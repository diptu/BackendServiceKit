"""FastAPI shared dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.dependencies import get_db
from app.services.session_service import SessionService


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


async def get_session_token(
    x_session_token: Annotated[str | None, Header()] = None,
) -> str:
    if not x_session_token:
        raise HTTPException(
            status_code=401, detail="X-Session-Token header is required."
        )
    return x_session_token


async def get_session_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionService:
    return SessionService(db)


TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
SessionTokenDep = Annotated[str, Depends(get_session_token)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
