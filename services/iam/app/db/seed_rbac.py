"""Idempotent seeding of the RBAC permission catalog and system roles.

Safe to invoke on every application startup: every insert is preceded by a
slug-based lookup, so re-running it is a no-op once the rows exist, and it
never revokes a permission an operator granted by hand afterwards.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    ORG_PERMISSIONS,
    ORG_ROLE_PERMISSIONS,
    PLATFORM_PERMISSIONS,
    PLATFORM_ROLE_PERMISSIONS,
    SYSTEM_ORG_ROLES,
    SYSTEM_ROLES,
)
from app.models.permission import Permission
from app.models.role import Role


async def _ensure_permissions(
    session: AsyncSession, slugs: list[str]
) -> dict[str, Permission]:
    """Look up or create each permission slug; returns slug -> Permission."""
    permission_map: dict[str, Permission] = {}
    for permission_slug in slugs:
        result = await session.execute(
            select(Permission).where(Permission.slug == permission_slug)
        )
        permission = result.scalar_one_or_none()
        if permission is None:
            resource, action = permission_slug.split(":", 1)
            permission = Permission(
                name=permission_slug.replace(":", " ").replace("_", " ").title(),
                slug=permission_slug,
                resource=resource,
                action=action,
                description=f"Permission to {action.replace('_', ' ')} {resource}.",
            )
            session.add(permission)
            await session.flush()
        permission_map[permission_slug] = permission
    return permission_map


async def _ensure_global_role(
    session: AsyncSession,
    *,
    slug: str,
    wanted_permission_slugs: list[str],
    permission_map: dict[str, Permission],
) -> None:
    """
    Ensure a global (organization_id IS NULL) role exists and holds at least
    `wanted_permission_slugs`.
    """
    result = await session.execute(
        select(Role).where(Role.slug == slug, Role.organization_id.is_(None))
    )
    role = result.scalar_one_or_none()
    if role is None:
        # Set permissions at construction time rather than reading
        # `.permissions` on a just-flushed object — accessing an unloaded
        # relationship on an object that wasn't returned by a SELECT
        # triggers a sync lazy-load incompatible with asyncio.
        role = Role(
            name=slug.replace("_", " ").title(),
            slug=slug,
            description=f"System-seeded role: {slug}",
            is_system=True,
            organization_id=None,
            permissions=[permission_map[s] for s in wanted_permission_slugs],
        )
        session.add(role)
        await session.flush()
        return

    # Existing role: lazy="selectin" already eager-loaded `.permissions` as
    # part of the SELECT above, so reading/appending here is safe.
    granted_slugs = {p.slug for p in role.permissions}
    for permission_slug in wanted_permission_slugs:
        if permission_slug not in granted_slugs:
            role.permissions.append(permission_map[permission_slug])


async def seed_org_rbac(session: AsyncSession) -> None:
    """Ensure org_owner/org_admin/org_member roles and their permissions exist."""
    permission_map = await _ensure_permissions(session, list(ORG_PERMISSIONS.values()))
    for org_role in SYSTEM_ORG_ROLES:
        await _ensure_global_role(
            session,
            slug=org_role.value,
            wanted_permission_slugs=ORG_ROLE_PERMISSIONS[org_role],
            permission_map=permission_map,
        )
    await session.commit()


async def seed_platform_rbac(session: AsyncSession) -> None:
    """Ensure platform RoleEnum roles (super_admin, admin, ...) and the
    users:*/roles:* permission catalog exist."""
    permission_map = await _ensure_permissions(
        session, list(PLATFORM_PERMISSIONS.values())
    )
    for platform_role in SYSTEM_ROLES:
        await _ensure_global_role(
            session,
            slug=platform_role.value,
            wanted_permission_slugs=PLATFORM_ROLE_PERMISSIONS[platform_role],
            permission_map=permission_map,
        )
    await session.commit()


async def seed_rbac_catalog(session: AsyncSession) -> None:
    """Convenience entrypoint: seeds both the platform and org RBAC catalogs."""
    await seed_platform_rbac(session)
    await seed_org_rbac(session)
