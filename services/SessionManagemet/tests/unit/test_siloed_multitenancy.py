"""Siloed (database-per-tenant) multi-tenancy: connection resolver, per-tenant
engine registry, tenant context, and SessionManagement's tenant-aware `get_db`.

The central proof is that isolation moves to the *connection*: a session
obtained for tenant A physically cannot read tenant B's database — no reliance
on the `tenant_id` column. See TODO.md → "Definition of done".
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from shared.db.registry import TenantEngineRegistry
from shared.db.resolver import (
    ControlPlaneUnavailableError,
    TemplateConnectionResolver,
)
from shared.db.tenant_context import (
    TenantContextError,
    current_tenant_or_none,
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_substitutes_tenant_hex() -> None:
    resolver = TemplateConnectionResolver("postgresql+asyncpg://h/session_{tenant}")
    tenant_id = uuid.uuid4()
    assert (
        await resolver.resolve(tenant_id)
        == f"postgresql+asyncpg://h/session_{tenant_id.hex}"
    )


@pytest.mark.asyncio
async def test_resolver_override_wins_over_template() -> None:
    tenant_id = uuid.uuid4()
    resolver = TemplateConnectionResolver(
        "postgresql+asyncpg://h/session_{tenant}",
        {str(tenant_id): "postgresql+asyncpg://other-host/session_special"},
    )
    assert (
        await resolver.resolve(tenant_id)
        == "postgresql+asyncpg://other-host/session_special"
    )


def test_resolver_requires_placeholder_or_override() -> None:
    with pytest.raises(ValueError):
        TemplateConnectionResolver("postgresql+asyncpg://static/iam")


@pytest.mark.asyncio
async def test_resolver_unmapped_tenant_fails_closed() -> None:
    # Overrides present (so construction is allowed) but no placeholder and no
    # entry for this tenant → must raise, never invent a fallback.
    resolver = TemplateConnectionResolver(
        "postgresql+asyncpg://static/iam", {str(uuid.uuid4()): "postgresql://x"}
    )
    with pytest.raises(ControlPlaneUnavailableError):
        await resolver.resolve(uuid.uuid4())


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _sqlite_registry(tmp_path: object, **kwargs: object) -> TenantEngineRegistry:
    template = f"sqlite+aiosqlite:///{tmp_path}/session_{{tenant}}.db"
    return TenantEngineRegistry(
        TemplateConnectionResolver(template),
        connect_args={"check_same_thread": False},
        **kwargs,
    )


@pytest.mark.asyncio
async def test_registry_gives_distinct_engines_and_caches_makers(
    tmp_path: object,
) -> None:
    registry = _sqlite_registry(tmp_path)
    a, b = uuid.uuid4(), uuid.uuid4()

    engine_a = await registry.engine_for(a)
    engine_b = await registry.engine_for(b)
    assert engine_a is not engine_b
    assert a.hex in str(engine_a.url)
    assert b.hex in str(engine_b.url)

    # Same tenant → the same cached session factory (pooling is preserved).
    assert await registry.sessionmaker_for(a) is await registry.sessionmaker_for(a)
    await registry.dispose_all()


@pytest.mark.asyncio
async def test_registry_isolates_tenant_data(tmp_path: object) -> None:
    registry = _sqlite_registry(tmp_path)
    a, b = uuid.uuid4(), uuid.uuid4()

    for tenant in (a, b):
        engine = await registry.engine_for(tenant)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY)"))

    maker_a = await registry.sessionmaker_for(a)
    async with maker_a() as session:
        await session.execute(text("INSERT INTO probe (id) VALUES (1)"))
        await session.commit()

    maker_b = await registry.sessionmaker_for(b)
    async with maker_b() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM probe"))).scalar()

    # Tenant B's connection cannot see tenant A's write — structural isolation.
    assert count == 0
    await registry.dispose_all()


@pytest.mark.asyncio
async def test_registry_evicts_beyond_max_engines(tmp_path: object) -> None:
    registry = _sqlite_registry(tmp_path, max_engines=1)
    a, b = uuid.uuid4(), uuid.uuid4()

    engine_a_first = await registry.engine_for(a)
    await registry.engine_for(b)  # exceeds max_engines=1 → evicts + disposes a
    engine_a_again = await registry.engine_for(a)  # rebuilt from scratch

    assert engine_a_first is not engine_a_again
    await registry.dispose_all()


# ---------------------------------------------------------------------------
# Tenant context (fail-closed)
# ---------------------------------------------------------------------------


def test_tenant_context_fails_closed_when_unset() -> None:
    assert current_tenant_or_none() is None
    with pytest.raises(TenantContextError):
        get_current_tenant()


def test_tenant_context_set_and_reset() -> None:
    tenant_id = uuid.uuid4()
    token = set_current_tenant(tenant_id)
    try:
        assert get_current_tenant() == tenant_id
    finally:
        reset_current_tenant(token)
    assert current_tenant_or_none() is None


# ---------------------------------------------------------------------------
# SessionManagement get_db routing
# ---------------------------------------------------------------------------


@pytest.fixture
def _fresh_registry() -> object:
    from app.infrastructure.database.tenant_routing import get_registry

    get_registry.cache_clear()
    yield
    get_registry.cache_clear()


@pytest.mark.asyncio
async def test_get_db_fails_closed_without_tenant(
    monkeypatch: pytest.MonkeyPatch, _fresh_registry: object
) -> None:
    from app.core.config import settings
    from app.infrastructure.database.dependencies import get_db

    monkeypatch.setattr(settings, "siloed_multitenancy_enabled", True)
    monkeypatch.setattr(
        settings,
        "tenant_database_url_template",
        "sqlite+aiosqlite:///./session_{tenant}.db",
    )

    gen = get_db(x_tenant_id=None)
    with pytest.raises(HTTPException) as exc_info:
        await anext(gen)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_db_routes_to_the_request_tenant_database(
    monkeypatch: pytest.MonkeyPatch, _fresh_registry: object, tmp_path: object
) -> None:
    from app.core.config import settings
    from app.infrastructure.database.dependencies import get_db
    from app.infrastructure.database.tenant_routing import (
        get_registry,
        get_tenant_engine,
    )

    monkeypatch.setattr(settings, "siloed_multitenancy_enabled", True)
    monkeypatch.setattr(
        settings,
        "tenant_database_url_template",
        f"sqlite+aiosqlite:///{tmp_path}/session_{{tenant}}.db",
    )

    tenant_id = uuid.uuid4()
    engine = await get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY)"))

    gen = get_db(x_tenant_id=tenant_id)
    session = await anext(gen)
    try:
        await session.execute(text("INSERT INTO probe (id) VALUES (7)"))
        value = (await session.execute(text("SELECT id FROM probe"))).scalar()
        assert value == 7
    finally:
        await gen.aclose()

    assert tenant_id.hex in str(engine.url)
    await get_registry().dispose_all()


@pytest.mark.asyncio
async def test_control_plane_resolver_is_wired(
    monkeypatch: pytest.MonkeyPatch, _fresh_registry: object, tmp_path: object
) -> None:
    """With tenant_resolver=control_plane, the registry drives the
    ControlPlaneConnectionResolver (which fetches each tenant's DSN from
    Tenent) and still produces a working per-tenant engine."""
    from app.core.config import settings
    from app.infrastructure.database.tenant_routing import (
        get_registry,
        get_tenant_engine,
    )
    from shared.db.resolver import ControlPlaneConnectionResolver

    monkeypatch.setattr(settings, "siloed_multitenancy_enabled", True)
    monkeypatch.setattr(settings, "tenant_resolver", "control_plane")
    monkeypatch.setattr(settings, "control_plane_base_url", "http://tenent.internal")

    async def _fake_resolve(
        _self: ControlPlaneConnectionResolver, tenant_id: uuid.UUID
    ) -> str:
        # Stand in for Tenent returning this tenant's DSN.
        return f"sqlite+aiosqlite:///{tmp_path}/cp_{tenant_id.hex}.db"

    monkeypatch.setattr(ControlPlaneConnectionResolver, "resolve", _fake_resolve)

    tenant_id = uuid.uuid4()
    engine = await get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY)"))

    assert tenant_id.hex in str(engine.url)
    await get_registry().dispose_all()
