"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.access_review import AccessReview
from app.models.attribute import Attribute
from app.models.audit_event import AuditEvent
from app.models.entitlement import Entitlement
from app.models.group import Group, GroupMembership
from app.models.membership import TenantMembership, UserRole
from app.models.permission import Permission, RolePermission
from app.models.role import Role
from app.models.user_projection import UserProjection

__all__ = [
    "AccessReview",
    "Attribute",
    "AuditEvent",
    "Entitlement",
    "Group",
    "GroupMembership",
    "Permission",
    "Role",
    "RolePermission",
    "TenantMembership",
    "UserProjection",
    "UserRole",
]
