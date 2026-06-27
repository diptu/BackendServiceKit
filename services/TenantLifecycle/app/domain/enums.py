"""Domain enumerations for the Tenant Lifecycle Service."""

from __future__ import annotations

from enum import StrEnum


class TenantLifecycleStatus(StrEnum):
    """All possible lifecycle states of a tenant."""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    ARCHIVED = "archived"
    DELETED = "deleted"


class TransitionType(StrEnum):
    """Named action types that drive lifecycle transitions."""

    ACTIVATE = "activate"
    SUSPEND = "suspend"
    REACTIVATE = "reactivate"
    LOCK = "lock"
    ARCHIVE = "archive"
    DELETE = "delete"


# Valid state transitions: from_state → {allowed to_states}
VALID_TRANSITIONS: dict[TenantLifecycleStatus, frozenset[TenantLifecycleStatus]] = {
    TenantLifecycleStatus.PROVISIONING: frozenset({TenantLifecycleStatus.ACTIVE}),
    TenantLifecycleStatus.ACTIVE: frozenset(
        {
            TenantLifecycleStatus.SUSPENDED,
            TenantLifecycleStatus.LOCKED,
            TenantLifecycleStatus.ARCHIVED,
        }
    ),
    TenantLifecycleStatus.SUSPENDED: frozenset(
        {TenantLifecycleStatus.ACTIVE, TenantLifecycleStatus.ARCHIVED}
    ),
    TenantLifecycleStatus.LOCKED: frozenset({TenantLifecycleStatus.ARCHIVED}),
    TenantLifecycleStatus.ARCHIVED: frozenset({TenantLifecycleStatus.DELETED}),
    TenantLifecycleStatus.DELETED: frozenset(),
}
