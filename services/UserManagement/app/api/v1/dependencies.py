"""FastAPI shared dependencies.

Every request is scoped to a tenant via the required `X-Tenant-ID` header.
Users are always looked up by (user_id, tenant_id) together so a caller in
tenant A can never fetch, update, or delete a user belonging to tenant B,
even by guessing its UUID — same rule every service in this repo follows.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.dependencies import get_db
from app.infrastructure.messaging.publisher import NullPublisher, RabbitMQPublisher
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.invitation_service import InvitationService
from app.services.user_service import UserService


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


def get_publisher(request: Request) -> RabbitMQPublisher | NullPublisher:
    """Fire-and-log publisher — real connection if RabbitMQ is up, a no-op
    otherwise. Matches services/APIGateway/app/api/v1/proxy_router.py's
    `_get_publisher` pattern (the only genuinely proven shape of this in
    this repo — see this service's TODO.md for why Tenent's own
    RabbitMQPublisher isn't the one being copied)."""
    conn = getattr(request.app.state, "rabbitmq_connection", None)
    if conn is not None and not conn.is_closed:
        return RabbitMQPublisher(conn)
    return NullPublisher()


async def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[RabbitMQPublisher | NullPublisher, Depends(get_publisher)],
) -> UserService:
    return UserService(db, publisher)


async def get_invitation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[RabbitMQPublisher | NullPublisher, Depends(get_publisher)],
) -> InvitationService:
    return InvitationService(db, publisher)


async def get_user_or_404(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
) -> User:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id, tenant_id=tenant_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    return user


DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
UserDep = Annotated[User, Depends(get_user_or_404)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]
