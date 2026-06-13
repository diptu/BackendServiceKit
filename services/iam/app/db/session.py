from __future__ import annotations

from collections.abc import AsyncGenerator

from app.core.config import settings
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.pool import NullPool

# Explicitly type hint global trackers so Mypy understands their state transitions
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Lazily initialize async engine + sessionmaker.
    """
    global _engine, _session_maker

    if _session_maker is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL must be set")

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            poolclass=NullPool,
        )

        _session_maker = async_sessionmaker(
            bind=_engine,
            expire_on_commit=False,
        )

    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()

    async with session_maker() as session:
        yield session


def get_engine() -> AsyncEngine:
    """
    Ensures the engine and session maker are initialized,
    then returns the active engine.
    """
    get_session_maker()  # Triggers the initialization block

    # Assert or check that _engine is truly populated to completely satisfy Mypy
    if _engine is None:
        raise RuntimeError("Database engine has not been properly initialized.")

    return _engine