"""Domain command objects.

Simple ID-only operations (role/permission assignment, group membership,
tenant membership) take plain UUID arguments in the service layer instead of
a command dataclass — a wrapper around one or two UUIDs adds no clarity.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import AttributeValueType, PolicyEffect


@dataclass
class CreateRoleCmd:
    tenant_id: UUID
    name: str
    description: str | None = None


@dataclass
class UpdateRoleCmd:
    name: str | None = None
    description: str | None = None


@dataclass
class CreatePermissionCmd:
    tenant_id: UUID
    name: str
    description: str | None = None


@dataclass
class UpdatePermissionCmd:
    name: str | None = None
    description: str | None = None


@dataclass
class CreateGroupCmd:
    tenant_id: UUID
    name: str
    description: str | None = None


@dataclass
class UpdateGroupCmd:
    name: str | None = None
    description: str | None = None


@dataclass
class CreateAttributeCmd:
    tenant_id: UUID
    user_id: UUID
    key: str
    value: str | float | bool | list[object]
    value_type: AttributeValueType


@dataclass
class UpdateAttributeCmd:
    value: str | float | bool | list[object] | None = None
    value_type: AttributeValueType | None = None


@dataclass
class CreateEntitlementCmd:
    tenant_id: UUID
    user_id: UUID
    key: str
    value: str | float | bool | list[object] | None = None


@dataclass
class CreateAccessReviewCmd:
    tenant_id: UUID
    subject_user_id: UUID
    resource_type: str
    resource_id: UUID
    reviewer_id: UUID | None = None


@dataclass
class UpdateAccessReviewCmd:
    status: str
    decision_notes: str | None = None
    reviewer_id: UUID | None = None


@dataclass
class CreatePolicyCmd:
    tenant_id: UUID
    name: str
    effect: PolicyEffect
    resource_type: str
    action: str
    description: str | None = None
    conditions: dict[str, object] | None = None
    priority: int = 0
    is_active: bool = True


@dataclass
class UpdatePolicyCmd:
    name: str | None = None
    description: str | None = None
    effect: PolicyEffect | None = None
    resource_type: str | None = None
    action: str | None = None
    conditions: dict[str, object] | None = None
    priority: int | None = None
    is_active: bool | None = None
