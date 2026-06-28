"""FastAPI dependencies for resource validation and service wiring.

These dependencies follow Rule 10 of the FastAPI production standard:
move record-existence checks out of route handlers and into reusable
``Depends``-able functions.  FastAPI caches dependencies per request, so
``get_db`` is called only once even when both a dependency and the handler
declare it.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import TenantNotFoundError
from app.infrastructure.database.dependencies import get_db
from app.infrastructure.database.models.tenant import Tenant
from app.infrastructure.repositories.tenant import TenantRepository


async def get_tenant_or_404(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve ``tenant_id`` to a ``Tenant`` row or raise 404.

    Use as a route dependency wherever the handler requires an existing tenant:

    .. code-block:: python

        @router.get("/{tenant_id}")
        async def get_tenant(tenant: Tenant = Depends(get_tenant_or_404)) -> ...:
            ...

    FastAPI maps ``TenantNotFoundError`` → 404 via the exception handler
    registered in ``app.main``.
    """
    tenant = await TenantRepository(db).get_by_id(tenant_id)
    if tenant is None:
        raise TenantNotFoundError(tenant_id)
    return tenant
