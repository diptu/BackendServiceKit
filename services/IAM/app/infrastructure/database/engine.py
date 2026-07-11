"""Database engine configuration."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.infrastructure.database.utils import resolve_ssl

_url, _connect_args = resolve_ssl(settings.database_url)
engine: AsyncEngine = create_async_engine(
    _url,
    connect_args=_connect_args,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)
