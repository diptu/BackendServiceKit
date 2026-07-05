"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


VALID_TRANSITIONS: dict[UserStatus, frozenset[UserStatus]] = {
    UserStatus.PENDING: frozenset({UserStatus.ACTIVE}),
    UserStatus.ACTIVE: frozenset({UserStatus.SUSPENDED, UserStatus.DEACTIVATED}),
    UserStatus.SUSPENDED: frozenset({UserStatus.ACTIVE, UserStatus.DEACTIVATED}),
    UserStatus.DEACTIVATED: frozenset(),
}


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"
