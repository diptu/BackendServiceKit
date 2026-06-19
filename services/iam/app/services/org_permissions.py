"""
Shared dynamic authorization helpers for organization-scoped RBAC.

These compute permission sets from the actual Role/Permission graph at
request time (rather than a hardcoded rank table), so they stay correct as
custom roles are created/edited per organization. The computed set is the
one piece of authorization state that can't ride in the JWT (org grants
change without a re-login, and a user may belong to many orgs), so lookups
go through a cache-aside `PermissionCache` (see app.core.cache) to keep the
hot path off the database.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.core.cache import PermissionCache, get_permission_cache
from app.core.config import settings
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.repositories.organization import OrganizationRepository


def _raw_permission_slugs(member: OrganizationMember) -> set[str]:
    return {p.slug for p in member.role.permissions}


def _cache_key(organization_id: UUID, member: OrganizationMember) -> str:
    role = member.role
    # Embedding the role's updated_at in the key means editing a role's
    # permissions (or reassigning a member to a different role) naturally
    # invalidates stale entries — no fan-out invalidation needed.
    return (
        f"org_perms:{organization_id}:{member.user_id}:{role.id}:"
        f"{role.updated_at.timestamp()}"
    )


async def get_member_permissions(
    organization_id: UUID,
    member: OrganizationMember,
    *,
    cache: PermissionCache | None = None,
) -> set[str]:
    """Cache-aside lookup of a member's effective org permission set."""
    active_cache = cache or get_permission_cache()
    key = _cache_key(organization_id, member)
    cached = await active_cache.get(key)
    if cached is not None:
        return cached
    computed = _raw_permission_slugs(member)
    await active_cache.set(key, computed, settings.ORG_PERMISSIONS_CACHE_TTL_SECONDS)
    return computed


async def require_org_membership(
    org_repo: OrganizationRepository,
    organization_id: UUID,
    *,
    user_id: UUID,
    is_superuser: bool,
) -> OrganizationMember | None:
    """Require the caller to be an active member of the org (superusers bypass)."""
    member = await org_repo.get_member(organization_id, user_id)
    if is_superuser:
        return member
    if member is None or not member.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )
    return member


async def require_org_permission(
    org_repo: OrganizationRepository,
    organization_id: UUID,
    *,
    user_id: UUID,
    is_superuser: bool,
    permission_slug: str,
    cache: PermissionCache | None = None,
) -> OrganizationMember | None:
    """Require the caller's org role to grant `permission_slug` (superusers bypass)."""
    member = await require_org_membership(
        org_repo, organization_id, user_id=user_id, is_superuser=is_superuser
    )
    if is_superuser:
        return member
    assert member is not None  # require_org_membership raised otherwise
    granted = await get_member_permissions(organization_id, member, cache=cache)
    if permission_slug not in granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action.",
        )
    return member


async def assert_can_grant_role(
    organization_id: UUID,
    granter_member: OrganizationMember | None,
    role: Role,
    *,
    is_superuser: bool,
    cache: PermissionCache | None = None,
) -> None:
    """
    Dynamic grant guard: a member may only hand out a role whose permissions
    are a subset of the permissions their own role already holds.
    """
    if is_superuser:
        return
    if granter_member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )
    granter_permissions = await get_member_permissions(
        organization_id, granter_member, cache=cache
    )
    role_permissions = {p.slug for p in role.permissions}
    if not role_permissions.issubset(granter_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot grant a role with permissions you do not hold.",
        )
