"""Reusable FastAPI dependency injections for isolation resources."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import PolicyNotFoundError
from app.infrastructure.database.dependencies import get_db
from app.models.isolation_policy import IsolationPolicy
from app.repositories.isolation_policy import IsolationPolicyRepository

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_policy_or_404(policy_id: UUID, db: DbDep) -> IsolationPolicy:
    repo = IsolationPolicyRepository(db)
    policy = await repo.get_by_id(policy_id)
    if policy is None:
        raise PolicyNotFoundError(policy_id)
    return policy


PolicyDep = Annotated[IsolationPolicy, Depends(get_policy_or_404)]
