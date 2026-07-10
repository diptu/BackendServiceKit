"""Per-tenant AsyncEngine / session-factory cache.

One `AsyncEngine` (and its connection pool) is created lazily per tenant on
first use and cached, because building an engine per request would defeat
pooling entirely. In production every tenant URL should point through
**PgBouncer** so N tenant pools don't exhaust Postgres; `max_engines` bounds
how many engines this process keeps hot, evicting (and disposing) the
least-recently-created beyond that.

Isolation is structural: a session obtained for tenant A is bound to tenant
A's engine and can only ever reach tenant A's database — the `tenant_id`
column becomes defense-in-depth rather than the isolation mechanism.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.db.resolver import TenantConnectionResolver


class TenantEngineRegistry:
    def __init__(
        self,
        resolver: TenantConnectionResolver,
        *,
        engine_kwargs: dict[str, Any] | None = None,
        connect_args: dict[str, Any] | None = None,
        max_engines: int | None = None,
    ) -> None:
        self._resolver = resolver
        self._engine_kwargs = dict(engine_kwargs or {})
        self._connect_args = dict(connect_args or {})
        self._max_engines = max_engines
        self._engines: OrderedDict[UUID, AsyncEngine] = OrderedDict()
        self._makers: dict[UUID, async_sessionmaker[AsyncSession]] = {}
        self._lock = asyncio.Lock()

    async def engine_for(self, tenant_id: UUID) -> AsyncEngine:
        engine = self._engines.get(tenant_id)
        if engine is not None:
            return engine
        await self._ensure(tenant_id)
        return self._engines[tenant_id]

    async def sessionmaker_for(
        self, tenant_id: UUID
    ) -> async_sessionmaker[AsyncSession]:
        maker = self._makers.get(tenant_id)
        if maker is not None:
            return maker
        await self._ensure(tenant_id)
        return self._makers[tenant_id]

    async def dispose_all(self) -> None:
        async with self._lock:
            for engine in self._engines.values():
                await engine.dispose()
            self._engines.clear()
            self._makers.clear()

    async def _ensure(self, tenant_id: UUID) -> None:
        async with self._lock:
            # Re-check under the lock — another coroutine may have built it.
            if tenant_id in self._makers:
                return
            url = await self._resolver.resolve(tenant_id)
            # The resolver may return any driver (a Control Plane hands back
            # whatever each tenant runs); SQLite needs check_same_thread off, so
            # add it per-URL rather than assuming a driver registry-wide.
            connect_args = dict(self._connect_args)
            if url.startswith("sqlite") and "check_same_thread" not in connect_args:
                connect_args["check_same_thread"] = False
            engine = create_async_engine(
                url, connect_args=connect_args, **self._engine_kwargs
            )
            self._engines[tenant_id] = engine
            self._makers[tenant_id] = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                autoflush=False,
                expire_on_commit=False,
            )
            await self._evict_if_needed()

    async def _evict_if_needed(self) -> None:
        if self._max_engines is None:
            return
        while len(self._engines) > self._max_engines:
            evicted_id, evicted_engine = self._engines.popitem(last=False)
            self._makers.pop(evicted_id, None)
            await evicted_engine.dispose()
