"""Domain-level validation for isolation operations."""

from __future__ import annotations

from uuid import UUID

from app.core.constants import MAX_RESOURCE_ID_LENGTH
from app.domain.enums import AccessAction, ResourceType
from app.domain.exceptions import InvalidQueryFilterError, IsolationValidationError


def validate_resource_ids(resource_ids: list[str]) -> None:
    for rid in resource_ids:
        if not rid or not rid.strip():
            raise IsolationValidationError("resource_ids must not contain blank entries.")
        if len(rid) > MAX_RESOURCE_ID_LENGTH:
            raise IsolationValidationError(
                f"resource_id exceeds maximum length of {MAX_RESOURCE_ID_LENGTH}: '{rid[:64]}'."
            )


def validate_resource_type(resource_type: str) -> None:
    valid = frozenset(rt.value for rt in ResourceType)
    if resource_type not in valid:
        raise IsolationValidationError(
            f"'{resource_type}' is not a valid resource type. Valid: {sorted(valid)}."
        )


def validate_access_action(action: str) -> None:
    valid = frozenset(a.value for a in AccessAction)
    if action not in valid:
        raise IsolationValidationError(
            f"'{action}' is not a valid access action. Valid: {sorted(valid)}."
        )


def validate_query_filter(query_filter: dict[str, str]) -> None:
    if "tenant_id" not in query_filter:
        raise InvalidQueryFilterError("Query filter missing required 'tenant_id' key.")


def validate_policy_update(
    allowed_partner_tenant_ids: list[str] | None,
) -> None:
    if allowed_partner_tenant_ids is None:
        return
    for entry in allowed_partner_tenant_ids:
        try:
            UUID(entry)
        except (ValueError, AttributeError) as exc:
            raise IsolationValidationError(
                f"allowed_partner_tenant_ids contains invalid UUID: '{entry}'."
            ) from exc
