"""SessionManagement's binding to the shared per-tenant connection router.

This is the thin, SessionManagement-specific glue: it constructs the shared
`TenantEngineRegistry` from SessionManagement's settings once, and hands out per-tenant
session factories. The routing/pooling/eviction logic itself lives in
`shared/db/` so User, Organization and Authentication reuse the identical
implementation (see TODO.md → "Build this once in shared/, not inside SessionManagement").
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import settings
from shared.db.registry import TenantEngineRegistry
from shared.db.resolver import (
    ControlPlaneConnectionResolver,
    TemplateConnectionResolver,
    TenantConnectionResolver,
)


def _build_resolver() -> TenantConnectionResolver:
    if settings.tenant_resolver == "control_plane":
        if not settings.control_plane_base_url:
            raise RuntimeError(
                "tenant_resolver=control_plane requires control_plane_base_url."
            )
        return ControlPlaneConnectionResolver(
            settings.control_plane_base_url, timeout=settings.control_plane_timeout
        )

    template = settings.tenant_database_url_template
    overrides = settings.tenant_database_overrides
    if not template and not overrides:
        raise RuntimeError(
            "siloed_multitenancy_enabled is on but neither "
            "tenant_database_url_template nor tenant_database_overrides is set."
        )
    return TemplateConnectionResolver(template=template or "", overrides=overrides)


@lru_cache
def get_registry() -> TenantEngineRegistry:
    """Process-wide per-tenant engine registry, built from SessionManagement settings.

    Cached so every request shares one set of tenant pools. Call
    `get_registry.cache_clear()` after mutating the relevant settings (tests
    do this)."""
    resolver = _build_resolver()

    # Pool tuning is driver-dependent. With the Control Plane resolver, tenants
    # may run different drivers (and go through PgBouncer), so use minimal
    # kwargs and let per-URL specifics (e.g. SQLite check_same_thread) be added
    # by the registry. With the template resolver we know the driver up front.
    connect_args: dict[str, Any]
    engine_kwargs: dict[str, Any]
    if settings.tenant_resolver == "control_plane":
        connect_args = {}
        engine_kwargs = {"pool_pre_ping": True}
    else:
        sample = settings.tenant_database_url_template or next(
            iter(settings.tenant_database_overrides.values()), ""
        )
        if sample.startswith("sqlite"):
            connect_args = {}
            engine_kwargs = {"pool_pre_ping": True}
        else:
            connect_args = {}
            engine_kwargs = {
                "pool_pre_ping": True,
                "pool_recycle": 1800,
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout,
            }

    return TenantEngineRegistry(
        resolver,
        engine_kwargs=engine_kwargs,
        connect_args=connect_args,
        max_engines=settings.tenant_max_engines,
    )


async def get_tenant_sessionmaker(
    tenant_id: UUID,
) -> async_sessionmaker[AsyncSession]:
    # Bound to a typed local because shared.* is treated as untyped here.
    maker: async_sessionmaker[AsyncSession] = await get_registry().sessionmaker_for(
        tenant_id
    )
    return maker


async def get_tenant_engine(tenant_id: UUID) -> AsyncEngine:
    """Used by the provisioning path to create/migrate a tenant's schema."""
    engine: AsyncEngine = await get_registry().engine_for(tenant_id)
    return engine
