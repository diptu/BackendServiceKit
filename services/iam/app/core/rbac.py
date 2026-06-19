from enum import StrEnum
from typing import Final


class RoleEnum(StrEnum):
    """
    System RBAC roles (authoritative source of truth).

    These roles are used across:
        - database seeding
        - JWT claims
        - authorization checks
        - policy engine
    """

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    AUDITOR = "auditor"
    SUPPORT = "support"
    SERVICE_ACCOUNT = "service_account"
    GUEST = "guest"
    USER = "user"


# ============================================================
# DEFAULT ROLE
# ============================================================

DEFAULT_ROLE: Final[RoleEnum] = RoleEnum.GUEST

# Role assigned after onboarding/verification
DEFAULT_VERIFIED_ROLE: Final[RoleEnum] = RoleEnum.USER

# First system bootstrap role
BOOTSTRAP_ROLE: Final[RoleEnum] = RoleEnum.SUPER_ADMIN


# ============================================================
# ROLE LISTS (useful for seeding)
# ============================================================

SYSTEM_ROLES: Final[list[RoleEnum]] = list(RoleEnum)


# ============================================================
# ROLE HELPERS
# ============================================================


def is_valid_role(role: str) -> bool:
    """
    Validate if a string is a valid system role.
    """
    return role in RoleEnum._value2member_map_


def to_role_enum(role: str | RoleEnum) -> RoleEnum:
    """
    Normalize input to RoleEnum.
    """
    if isinstance(role, RoleEnum):
        return role
    return RoleEnum(role)


# ============================================================
# ORGANIZATION (MULTI-TENANT) ROLES
# ============================================================
#
# These are distinct from the platform-wide RoleEnum above: they govern
# what a user may do *inside one specific organization* and are stored
# as ordinary `Role` rows with `organization_id IS NULL` + `is_system=True`
# so they can be referenced by id from any tenant's OrganizationMember rows
# without duplication.


class OrgRoleEnum(StrEnum):
    """System-seeded roles for organization membership."""

    OWNER = "org_owner"
    ADMIN = "org_admin"
    MEMBER = "org_member"


DEFAULT_ORG_ROLE: Final[OrgRoleEnum] = OrgRoleEnum.MEMBER

SYSTEM_ORG_ROLES: Final[list[OrgRoleEnum]] = list(OrgRoleEnum)

# Resource:action permission slugs available on the `organizations` resource.
ORG_PERMISSIONS: Final[dict[str, str]] = {
    "read": "organizations:read",
    "update": "organizations:update",
    "delete": "organizations:delete",
    "manage_members": "organizations:manage_members",
    "manage_roles": "organizations:manage_roles",
}

# Permission slugs granted to each seeded org role.
ORG_ROLE_PERMISSIONS: Final[dict[OrgRoleEnum, list[str]]] = {
    OrgRoleEnum.OWNER: list(ORG_PERMISSIONS.values()),
    OrgRoleEnum.ADMIN: [
        ORG_PERMISSIONS["read"],
        ORG_PERMISSIONS["update"],
        ORG_PERMISSIONS["manage_members"],
        ORG_PERMISSIONS["manage_roles"],
    ],
    OrgRoleEnum.MEMBER: [ORG_PERMISSIONS["read"]],
}


def is_valid_org_role(role: str) -> bool:
    """Validate if a string is a valid seeded organization role slug."""
    return role in OrgRoleEnum._value2member_map_


# ============================================================
# PLATFORM PERMISSION CATALOG
# ============================================================
#
# Global (organization_id IS NULL) permissions, attached to the platform
# RoleEnum roles above. These are embedded directly in JWT claims at login
# (see AuthService) so platform-scoped authorization checks never touch the
# database — `require_permission()` just inspects the token.

PLATFORM_PERMISSIONS: Final[dict[str, str]] = {
    "users_create": "users:create",
    "users_read": "users:read",
    "users_update": "users:update",
    "users_delete": "users:delete",
    "roles_read": "roles:read",
    "roles_manage": "roles:manage",
}

# Default permission slugs granted to each seeded platform role. Purely
# additive at seed time — never revokes a permission an operator already
# granted manually.
PLATFORM_ROLE_PERMISSIONS: Final[dict[RoleEnum, list[str]]] = {
    RoleEnum.SUPER_ADMIN: list(PLATFORM_PERMISSIONS.values()),
    RoleEnum.ADMIN: [
        PLATFORM_PERMISSIONS["users_create"],
        PLATFORM_PERMISSIONS["users_read"],
        PLATFORM_PERMISSIONS["users_update"],
        PLATFORM_PERMISSIONS["users_delete"],
        PLATFORM_PERMISSIONS["roles_read"],
    ],
    RoleEnum.MANAGER: [
        PLATFORM_PERMISSIONS["users_read"],
        PLATFORM_PERMISSIONS["users_update"],
    ],
    RoleEnum.OPERATOR: [PLATFORM_PERMISSIONS["users_read"]],
    RoleEnum.AUDITOR: [
        PLATFORM_PERMISSIONS["users_read"],
        PLATFORM_PERMISSIONS["roles_read"],
    ],
    RoleEnum.SUPPORT: [PLATFORM_PERMISSIONS["users_read"]],
    RoleEnum.SERVICE_ACCOUNT: [],
    RoleEnum.GUEST: [],
    RoleEnum.USER: [],
}
