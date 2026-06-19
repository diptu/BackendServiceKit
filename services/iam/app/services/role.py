from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.rbac import ORG_PERMISSIONS
from app.models.role import Role
from app.repositories.organization import OrganizationRepository
from app.repositories.role import RoleRepository
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.schemas.user import UserOut
from app.services.org_permissions import require_org_membership, require_org_permission


class RoleService:
    """
    CRUD for roles, spanning both:
      - global/platform roles (organization_id is None) — platform-admin only
      - custom roles scoped to one organization — gated by that org's
        `organizations:manage_roles` permission
    """

    def __init__(
        self,
        role_repo: RoleRepository,
        org_repo: OrganizationRepository,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._roles = role_repo
        self._orgs = org_repo
        self._audit = audit_logger

    async def list_roles(
        self, current_user: UserOut, organization_id: UUID | None
    ) -> list[RoleOut]:
        if organization_id is not None:
            await require_org_membership(
                self._orgs,
                organization_id,
                user_id=current_user.id,
                is_superuser=current_user.is_superuser,
            )
            roles = await self._roles.list_roles(
                organization_id=organization_id, include_global=True
            )
        else:
            roles = await self._roles.list_roles(organization_id=None)
        return [RoleOut.model_validate(r) for r in roles]

    async def get_role(self, role_id: UUID, current_user: UserOut) -> RoleOut:
        role = await self._get_or_404(role_id)
        if role.organization_id is not None:
            await require_org_membership(
                self._orgs,
                role.organization_id,
                user_id=current_user.id,
                is_superuser=current_user.is_superuser,
            )
        return RoleOut.model_validate(role)

    async def create_role(
        self,
        data: RoleCreate,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RoleOut:
        if data.organization_id is None:
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only platform admins can create global roles.",
                )
        else:
            await require_org_permission(
                self._orgs,
                data.organization_id,
                user_id=current_user.id,
                is_superuser=current_user.is_superuser,
                permission_slug=ORG_PERMISSIONS["manage_roles"],
            )

        if await self._roles.get_by_slug(
            data.slug, organization_id=data.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role with this slug already exists in this scope.",
            )

        permissions = await self._roles.get_permissions_by_slugs(data.permission_slugs)
        found_slugs = {p.slug for p in permissions}
        missing = set(data.permission_slugs) - found_slugs
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown permission slug(s): {', '.join(sorted(missing))}",
            )

        role = Role(
            name=data.name,
            slug=data.slug,
            description=data.description,
            organization_id=data.organization_id,
            is_system=False,
        )
        role.permissions = permissions
        role = await self._roles.create(role)
        if self._audit:
            self._audit.log(
                AuditEventType.ROLE_CREATED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "role_id": str(role.id),
                    "slug": role.slug,
                    "organization_id": str(data.organization_id)
                    if data.organization_id
                    else None,
                },
            )
        return RoleOut.model_validate(role)

    async def update_role(
        self,
        role_id: UUID,
        data: RoleUpdate,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RoleOut:
        role = await self._get_or_404(role_id)
        await self._require_role_mutation_rights(role, current_user)

        if data.name is not None:
            role.name = data.name
        if data.slug is not None:
            role.slug = data.slug
        if data.description is not None:
            role.description = data.description
        role = await self._roles.save(role)
        if self._audit:
            self._audit.log(
                AuditEventType.ROLE_UPDATED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"role_id": str(role.id), "slug": role.slug},
            )
        return RoleOut.model_validate(role)

    async def delete_role(
        self,
        role_id: UUID,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        role = await self._get_or_404(role_id)
        await self._require_role_mutation_rights(role, current_user)

        if await self._orgs.count_members_with_role(role_id) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role is still assigned to members; reassign them first.",
            )
        await self._roles.delete(role)
        if self._audit:
            self._audit.log(
                AuditEventType.ROLE_DELETED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"role_id": str(role_id), "slug": role.slug},
            )

    async def add_permissions(
        self,
        role_id: UUID,
        permission_slugs: list[str],
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RoleOut:
        role = await self._get_or_404(role_id)
        await self._require_role_mutation_rights(role, current_user)

        permissions = await self._roles.get_permissions_by_slugs(permission_slugs)
        found_slugs = {p.slug for p in permissions}
        missing = set(permission_slugs) - found_slugs
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown permission slug(s): {', '.join(sorted(missing))}",
            )

        held_slugs = {p.slug for p in role.permissions}
        newly_granted = [p.slug for p in permissions if p.slug not in held_slugs]
        for permission in permissions:
            if permission.slug not in held_slugs:
                role.permissions.append(permission)
        role = await self._roles.save(role)
        if self._audit:
            self._audit.log(
                AuditEventType.PERMISSION_ASSIGNED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"role_id": str(role.id), "permission_slugs": newly_granted},
            )
        return RoleOut.model_validate(role)

    async def remove_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RoleOut:
        role = await self._get_or_404(role_id)
        await self._require_role_mutation_rights(role, current_user)

        removed_slugs = [p.slug for p in role.permissions if p.id == permission_id]
        role.permissions = [p for p in role.permissions if p.id != permission_id]
        role = await self._roles.save(role)
        if self._audit:
            self._audit.log(
                AuditEventType.PERMISSION_REMOVED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"role_id": str(role.id), "permission_slugs": removed_slugs},
            )
        return RoleOut.model_validate(role)

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    async def _get_or_404(self, role_id: UUID) -> Role:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found."
            )
        return role

    async def _require_role_mutation_rights(
        self, role: Role, current_user: UserOut
    ) -> None:
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System roles cannot be modified or deleted.",
            )
        if role.organization_id is None:
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only platform admins can modify global roles.",
                )
        else:
            await require_org_permission(
                self._orgs,
                role.organization_id,
                user_id=current_user.id,
                is_superuser=current_user.is_superuser,
                permission_slug=ORG_PERMISSIONS["manage_roles"],
            )
