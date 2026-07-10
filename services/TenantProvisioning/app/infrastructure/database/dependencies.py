"""FastAPI database dependencies.

TenantProvisioning is a **global orchestrator** — its ProvisioningJob table
spans all tenants (it is the thing that *creates* per-tenant databases), so it
is intentionally NOT database-per-tenant. A single shared database, like the
Control Plane it works alongside.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per request."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
