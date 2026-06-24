"""FastAPI database dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.infrastructure.database.session import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session per request.

    Ensures proper cleanup and transaction isolation.
    """

    async with SessionLocal() as session:
        yield session