"""FastAPI database dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per request.

    Commits on clean return; rolls back and re-raises on any exception.
    This ensures every successful response is durable and every failed
    response leaves the database unchanged.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
