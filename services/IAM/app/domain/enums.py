"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class EntityStatus(StrEnum):
    """Shared active/deleted lifecycle for Role, Permission, and Group."""

    ACTIVE = "active"
    DELETED = "deleted"


VALID_ENTITY_TRANSITIONS: dict[EntityStatus, frozenset[EntityStatus]] = {
    EntityStatus.ACTIVE: frozenset({EntityStatus.DELETED}),
    EntityStatus.DELETED: frozenset(),
}


class MembershipStatus(StrEnum):
    """Status of a user's membership within a tenant."""

    ACTIVE = "active"
    REMOVED = "removed"


class AttributeValueType(StrEnum):
    """Declares how an attribute's JSON value should be interpreted."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"


class EntitlementStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class AccessReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"


class PolicyEffect(StrEnum):
    """What an AbacPolicy does when its conditions match."""

    ALLOW = "allow"
    DENY = "deny"


class ConditionOperator(StrEnum):
    """Comparison operators supported by an AbacPolicy condition leaf."""

    EQ = "eq"
    NE = "ne"
    IN = "in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EXISTS = "exists"


class AuditEventType(StrEnum):
    """Every authorization-changing operation this service audits.

    Deliberately scoped to grant/revoke relationships (who has access to
    what), not generic CRUD on Role/Permission/Group definitions
    themselves — see AuditEvent's docstring.
    """

    ROLE_ASSIGNED = "role.assigned"
    ROLE_UNASSIGNED = "role.unassigned"
    ROLE_PERMISSION_ADDED = "role.permission_added"
    ROLE_PERMISSION_REMOVED = "role.permission_removed"
    GROUP_MEMBER_ADDED = "group.member_added"
    GROUP_MEMBER_REMOVED = "group.member_removed"
    TENANT_MEMBERSHIP_ADDED = "tenant_membership.added"
    TENANT_MEMBERSHIP_REMOVED = "tenant_membership.removed"
    ENTITLEMENT_GRANTED = "entitlement.granted"
    ENTITLEMENT_REVOKED = "entitlement.revoked"
