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
