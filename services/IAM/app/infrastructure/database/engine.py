"""Database engine configuration."""

from __future__ import annotations

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)