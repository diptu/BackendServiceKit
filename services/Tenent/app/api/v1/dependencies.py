"""FastAPI shared dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import PolicyNotFoundError, TenantNotFoundError
from app.infrastructure.database.dependencies import get_db
from app.models.isolation_policy import IsolationPolicy
from app.models.tenant import Tenant
from app.repositories.isolation_policy import IsolationPolicyRepository
from app.repositories.tenant import TenantRepository


async def get_tenant_or_404(
    tenant_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    repo = TenantRepository(db)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found.")
    return tenant


async def get_policy_or_404(
    policy_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IsolationPolicy:
    repo = IsolationPolicyRepository(db)
    policy = await repo.get_by_id(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found.")
    return policy


TenantDep = Annotated[Tenant, Depends(get_tenant_or_404)]
PolicyDep = Annotated[IsolationPolicy, Depends(get_policy_or_404)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
