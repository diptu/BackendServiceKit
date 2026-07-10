"""Domain enumerations.

UserStatus merges UserManagement's own pending/active/suspended/deactivated
with UserLifecycleManagement's superset that added `locked`. Now that both
services are one, `locked` is a first-class status on User.status directly
— no more "locked proxies to suspended in the other service" indirection,
since there is no other service anymore.
"""

from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DEACTIVATED = "deactivated"


VALID_TRANSITIONS: dict[UserStatus, frozenset[UserStatus]] = {
    UserStatus.PENDING: frozenset({UserStatus.ACTIVE}),
    UserStatus.ACTIVE: frozenset(
        {UserStatus.SUSPENDED, UserStatus.LOCKED, UserStatus.DEACTIVATED}
    ),
    UserStatus.SUSPENDED: frozenset({UserStatus.ACTIVE, UserStatus.DEACTIVATED}),
    # locked is reversible via unlock only — matches Tenant's own `locked`
    # state (CLAUDE.md's Tenant Lifecycle States table).
    UserStatus.LOCKED: frozenset({UserStatus.ACTIVE}),
    UserStatus.DEACTIVATED: frozenset(),
}


class StatusChangeAction(StrEnum):
    """Distinguishes verbs that land on the same to_status (activate vs
    onboard both end in ACTIVE) — merged from UserLifecycleManagement's
    EventType, now recorded directly in UserStatusHistory."""

    ACTIVATE = "activate"
    ONBOARD = "onboard"
    DEACTIVATE = "deactivate"
    OFFBOARD = "offboard"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    LOCK = "lock"
    UNLOCK = "unlock"
    RESTORE = "restore"


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"
