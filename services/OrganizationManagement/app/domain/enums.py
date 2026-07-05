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
