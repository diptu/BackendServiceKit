"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class LifecycleStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DEACTIVATED = "deactivated"


VALID_TRANSITIONS: dict[LifecycleStatus, frozenset[LifecycleStatus]] = {
    LifecycleStatus.PENDING: frozenset({LifecycleStatus.ACTIVE}),
    LifecycleStatus.ACTIVE: frozenset(
        {LifecycleStatus.SUSPENDED, LifecycleStatus.LOCKED, LifecycleStatus.DEACTIVATED}
    ),
    LifecycleStatus.SUSPENDED: frozenset(
        {LifecycleStatus.ACTIVE, LifecycleStatus.DEACTIVATED}
    ),
    # locked is this-service-only, reversible via unlock only — matches
    # Tenant's own `locked` state exactly (see CLAUDE.md's Tenant Lifecycle
    # States table).
    LifecycleStatus.LOCKED: frozenset({LifecycleStatus.ACTIVE}),
    LifecycleStatus.DEACTIVATED: frozenset(),
}


class EventType(StrEnum):
    ACTIVATE = "activate"
    ONBOARD = "onboard"
    DEACTIVATE = "deactivate"
    OFFBOARD = "offboard"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    LOCK = "lock"
    UNLOCK = "unlock"
    RESTORE = "restore"
