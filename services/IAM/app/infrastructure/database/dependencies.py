"""FastAPI database dependencies.

`get_db` operates in one of two modes, controlled by
`settings.siloed_multitenancy_enabled`:

- **Shared-schema (default):** yields a session against the single
  `database_url` database — the historical behaviour, unchanged.
- **Siloed (database-per-tenant):** routes to the request tenant's own
  database, resolved from the `X-Tenant-ID` header (which the gateway derives
  from the subdomain). A request with no tenant **fails closed** with 400 —
  there is deliberately no fallback to a shared database.

The `tenant_id` column scoping in the repositories stays in both modes as
defense-in-depth; in siloed mode isolation is primarily enforced by the
connection itself.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.tenant_routing import get_tenant_sessionmaker


async def get_db(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per request."""
    if settings.siloed_multitenancy_enabled:
        if x_tenant_id is None:
            raise HTTPException(
                status_code=400, detail="X-Tenant-ID header is required."
            )
        session_factory = await get_tenant_sessionmaker(x_tenant_id)
    else:
        session_factory = SessionLocal

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
