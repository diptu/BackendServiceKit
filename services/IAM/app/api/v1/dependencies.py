"""FastAPI shared dependencies.

Every request is scoped to a tenant via the required `X-Tenant-ID` header —
no cross-service validation of that tenant_id against Tenent (trusted as-is;
see services/IAM/TODO.md for why). Each `get_<x>_or_404` dependency looks
entities up by (id, tenant_id) together so a caller in tenant A can never
fetch, update, or delete an entity belonging to tenant B, even by guessing
its UUID.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.dependencies import get_db
from app.models.group import Group
from app.models.permission import Permission
from app.models.role import Role
from app.repositories.group import GroupRepository
from app.repositories.permission import PermissionRepository
from app.repositories.role import RoleRepository
from app.services.access_review_service import AccessReviewService
from app.services.attribute_service import AttributeService
from app.services.entitlement_service import EntitlementService
from app.services.group_service import GroupService
from app.services.membership_service import MembershipService
from app.services.permission_service import PermissionService
from app.services.role_service import RoleService
from app.services.user_service import UserService


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


async def get_role_service(db: Annotated[AsyncSession, Depends(get_db)]) -> RoleService:
    return RoleService(db)


async def get_permission_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionService:
    return PermissionService(db)


async def get_group_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GroupService:
    return GroupService(db)


async def get_membership_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MembershipService:
    return MembershipService(db)


async def get_attribute_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttributeService:
    return AttributeService(db)


async def get_entitlement_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EntitlementService:
    return EntitlementService(db)


async def get_access_review_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessReviewService:
    return AccessReviewService(db)


async def get_user_service(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    return UserService(db)


# ---------------------------------------------------------------------------
# Path-param resolution (404 dependencies)
# ---------------------------------------------------------------------------


async def get_role_or_404(
    role_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
) -> Role:
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id, tenant_id=tenant_id)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found.")
    return role


async def get_permission_or_404(
    permission_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
) -> Permission:
    repo = PermissionRepository(db)
    permission = await repo.get_by_id(permission_id, tenant_id=tenant_id)
    if permission is None:
        raise HTTPException(
            status_code=404, detail=f"Permission {permission_id} not found."
        )
    return permission


async def get_group_or_404(
    group_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
) -> Group:
    repo = GroupRepository(db)
    group = await repo.get_by_id(group_id, tenant_id=tenant_id)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found.")
    return group


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]

RoleDep = Annotated[Role, Depends(get_role_or_404)]
PermissionDep = Annotated[Permission, Depends(get_permission_or_404)]
GroupDep = Annotated[Group, Depends(get_group_or_404)]

RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
GroupServiceDep = Annotated[GroupService, Depends(get_group_service)]
MembershipServiceDep = Annotated[MembershipService, Depends(get_membership_service)]
AttributeServiceDep = Annotated[AttributeService, Depends(get_attribute_service)]
EntitlementServiceDep = Annotated[EntitlementService, Depends(get_entitlement_service)]
AccessReviewServiceDep = Annotated[
    AccessReviewService, Depends(get_access_review_service)
]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
