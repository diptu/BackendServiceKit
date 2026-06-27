"""Database engine configuration."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.infrastructure.database.utils import resolve_ssl


def _build_engine() -> AsyncEngine:
    """Create the async engine with SSL handled via connect_args.

    asyncpg 0.29+ does not accept ``sslmode`` as a URL keyword argument.
    :func:`resolve_ssl` strips those params and returns an SSLContext when
    needed, keeping the engine creation compatible with both local Postgres
    and cloud providers like Neon.tech.
    """
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
