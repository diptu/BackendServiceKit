"""Database engine configuration (shared-schema mode).

In Siloed mode, per-request routing is handled by `tenant_routing.py` /
`get_db`; this module is the single shared-schema engine used when
`siloed_multitenancy_enabled` is off.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)
