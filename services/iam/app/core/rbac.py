from enum import Enum
from typing import Final


class RoleEnum(str, Enum):
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