"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


VALID_TRANSITIONS: dict[OrganizationStatus, frozenset[OrganizationStatus]] = {
    OrganizationStatus.ACTIVE: frozenset({OrganizationStatus.DELETED}),
    OrganizationStatus.DELETED: frozenset(),
}


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"


class TeamType(StrEnum):
    TEAM = "team"
    DEPARTMENT = "department"


class TeamStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"
