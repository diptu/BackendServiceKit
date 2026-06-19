from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.rbac import DEFAULT_ORG_ROLE, ORG_PERMISSIONS, OrgRoleEnum
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.repositories.organization import OrganizationRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.organization import (
    MemberAddRequest,
    MemberRoleUpdateRequest,
    OrganizationCreate,
    OrganizationDetailOut,
    OrganizationMemberOut,
    OrganizationOut,
    OrganizationPageResponse,
    OrganizationUpdate,
)
from app.schemas.user import UserOut
from app.services.org_permissions import assert_can_grant_role, require_org_permission


class OrganizationService:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        role_repo: RoleRepository,
        user_repo: UserRepository,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._orgs = org_repo
        self._roles = role_repo
        self._users = user_repo
        self._audit = audit_logger

    # -----------------------------------------------------------------
    # Organization CRUD
    # -----------------------------------------------------------------

    async def create_organization(
        self, creator: UserOut, data: OrganizationCreate
    ) -> OrganizationDetailOut:
        if await self._orgs.get_by_slug(data.slug) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization slug already taken.",
            )
        owner_role = await self._roles.get_by_slug(OrgRoleEnum.OWNER.value)
        if owner_role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization RBAC roles are not seeded.",
            )

        organization = await self._orgs.create(
            Organization(
                name=data.name,
                slug=data.slug,
                description=data.description,
                owner_id=creator.id,
            )
        )
        await self._orgs.add_member(
            OrganizationMember(
                organization_id=organization.id,
                user_id=creator.id,
                role_id=owner_role.id,
                invited_by=creator.id,
            )
        )
        organization = await self._get_or_404(organization.id)
        return OrganizationDetailOut.model_validate(organization)

    async def list_organizations(
        self, current_user: UserOut, *, page: int, page_size: int
    ) -> OrganizationPageResponse:
        if current_user.is_superuser:
            orgs, total = await self._orgs.list_all(page=page, page_size=page_size)
        else:
            orgs, total = await self._orgs.list_for_user(
                current_user.id, page=page, page_size=page_size
            )
        items = [OrganizationOut.model_validate(o) for o in orgs]
        return OrganizationPageResponse.build(items, total, page, page_size)

    async def get_organization(
        self, organization_id: UUID, current_user: UserOut
    ) -> OrganizationDetailOut:
        organization = await self._get_or_404(organization_id)
        await require_org_permission(
            self._orgs,
            organization_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            permission_slug=ORG_PERMISSIONS["read"],
        )
        return OrganizationDetailOut.model_validate(organization)

    async def update_organization(
        self,
        organization_id: UUID,
        data: OrganizationUpdate,
        current_user: UserOut,
    ) -> OrganizationDetailOut:
        organization = await self._get_or_404(organization_id)
        await require_org_permission(
            self._orgs,
            organization_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            permission_slug=ORG_PERMISSIONS["update"],
        )
        if data.name is not None:
            organization.name = data.name
        if data.description is not None:
            organization.description = data.description
        if data.is_active is not None:
            organization.is_active = data.is_active
        organization = await self._orgs.save(organization)
        return OrganizationDetailOut.model_validate(organization)

    async def delete_organization(
        self, organization_id: UUID, current_user: UserOut
    ) -> None:
        organization = await self._get_or_404(organization_id)
        await require_org_permission(
            self._orgs,
            organization_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            permission_slug=ORG_PERMISSIONS["delete"],
        )
        await self._orgs.delete(organization)

    # -----------------------------------------------------------------
    # Membership
    # -----------------------------------------------------------------

    async def list_members(
        self, organization_id: UUID, current_user: UserOut
    ) -> list[OrganizationMemberOut]:
        await self._get_or_404(organization_id)
        await require_org_permission(
            self._orgs,
            organization_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            permission_slug=ORG_PERMISSIONS["read"],
        )
        members = await self._orgs.list_members(organization_id)
        return [OrganizationMemberOut.model_validate(m) for m in members]

    async def add_member(
        self,
        organization_id: UUID,
        data: MemberAddRequest,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> OrganizationMemberOut:
        await self._get_or_404(organization_id)
        granter = await require_org_permission(
            self._orgs,
            organization_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            permission_slug=ORG_PERMISSIONS["manage_members"],
        )

        target_user = await self._users.get_by_id(data.user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        if await self._orgs.get_member(organization_id, data.user_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization.",
            )

        role = await self._resolve_role(organization_id, data.role_id, data.role_slug)
        await assert_can_grant_role(
            organization_id, granter, role, is_superuser=current_user.is_superuser
        )

        member = await self._orgs.add_member(
            OrganizationMember(
                organization_id=organization_id,
                user_id=data.user_id,
                role_id=role.id,
                invited_by=current_user.id,
            )
        )
        if self._audit:
            self._audit.log(
                AuditEventType.ORG_MEMBER_ADDED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "organization_id": str(organization_id),
                    "target_user_id": str(data.user_id),
                    "role_slug": role.slug,
                },
            )
        return OrganizationMemberOut.model_validate(member)

    async def update_member_role(
        self,
        organization_id: UUID,
        target_user_id: UUID,
        data: MemberRoleUpdateRequest,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> OrganizationMemberOut:
        await self._get_or_404(organization_id)
        granter = await require_org_permission(
            self._orgs,
            organization_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            permission_slug=ORG_PERMISSIONS["manage_members"],
        )

        target_member = await self._orgs.get_member(organization_id, target_user_id)
        if target_member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found."
            )

        new_role = await self._resolve_role(
            organization_id, data.role_id, data.role_slug
        )
        await assert_can_grant_role(
            organization_id, granter, new_role, is_superuser=current_user.is_superuser
        )

        if (
            target_member.role.slug == OrgRoleEnum.OWNER.value
            and new_role.slug != OrgRoleEnum.OWNER.value
            and await self._orgs.count_active_owners(organization_id) <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote the only remaining owner.",
            )

        role_before = target_member.role.slug
        target_member.role_id = new_role.id
        target_member = await self._orgs.save_member(target_member)
        if self._audit:
            self._audit.log(
                AuditEventType.ORG_MEMBER_ROLE_ASSIGNED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "organization_id": str(organization_id),
                    "target_user_id": str(target_user_id),
                    "role_before": role_before,
                    "role_after": new_role.slug,
                },
            )
        return OrganizationMemberOut.model_validate(target_member)

    async def remove_member(
        self,
        organization_id: UUID,
        target_user_id: UUID,
        current_user: UserOut,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._get_or_404(organization_id)
        target_member = await self._orgs.get_member(organization_id, target_user_id)
        if target_member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found."
            )

        is_self_removal = current_user.id == target_user_id
        if not is_self_removal:
            await require_org_permission(
                self._orgs,
                organization_id,
                user_id=current_user.id,
                is_superuser=current_user.is_superuser,
                permission_slug=ORG_PERMISSIONS["manage_members"],
            )

        if (
            target_member.role.slug == OrgRoleEnum.OWNER.value
            and await self._orgs.count_active_owners(organization_id) <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the only remaining owner.",
            )

        await self._orgs.remove_member(target_member)
        if self._audit:
            self._audit.log(
                AuditEventType.ORG_MEMBER_REMOVED,
                user_id=str(current_user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "organization_id": str(organization_id),
                    "target_user_id": str(target_user_id),
                    "self_removal": is_self_removal,
                },
            )

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    async def _get_or_404(self, organization_id: UUID) -> Organization:
        organization = await self._orgs.get_by_id(organization_id)
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
        return organization

    async def _resolve_role(
        self,
        organization_id: UUID,
        role_id: UUID | None,
        role_slug: str | None,
    ) -> Role:
        role: Role | None
        if role_id is not None:
            role = await self._roles.get_by_id(role_id)
        elif role_slug is not None:
            role = await self._roles.get_by_slug(
                role_slug, organization_id=organization_id
            )
            if role is None:
                role = await self._roles.get_by_slug(role_slug, organization_id=None)
        else:
            role = await self._roles.get_by_slug(DEFAULT_ORG_ROLE.value)

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found."
            )
        if role.organization_id is not None and role.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role does not belong to this organization.",
            )
        return role
