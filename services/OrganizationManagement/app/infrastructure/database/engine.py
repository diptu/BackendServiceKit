"""Database engine configuration."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.infrastructure.database.utils import resolve_ssl


def _build_engine() -> AsyncEngine:
    url, connect_args = resolve_ssl(settings.database_url)
    return create_async_engine(
        url,
        connect_args=connect_args,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
    )


engine: AsyncEngine = _build_engine()
