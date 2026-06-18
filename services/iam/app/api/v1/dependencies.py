from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import is_authenticated
from app.db.session import get_db as _get_db
from app.repositories.user import UserRepository
from app.schemas.user import UserOut


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency provider yielding an active asynchronous SQLAlchemy session matrix.
    Bridges the lower-level DB utilities directly into FastAPI's dependency injection system.
    """
    async for session in _get_db():
        yield session


async def get_current_user(
    claims: Annotated[dict[str, object], Depends(is_authenticated)],
    db: AsyncSession = Depends(get_async_db),
) -> UserOut:
    """Resolves JWT claims to a live, active User row and returns its public schema."""
    user = await UserRepository(db).get_by_id(UUID(str(claims["sub"])))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserOut.model_validate(user)
