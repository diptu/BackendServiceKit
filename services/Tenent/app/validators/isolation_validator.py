"""Input validators for isolation API requests."""

from __future__ import annotations

from uuid import UUID

from app.domain.enums import AccessAction, PolicyType, ResourceType
from app.domain.exceptions import IsolationValidationError


def validate_resource_type(value: str) -> ResourceType:
    try:
        return ResourceType(value)
    except ValueError:
        valid = ", ".join(e.value for e in ResourceType)
        raise IsolationValidationError(
            f"Invalid resource_type '{value}'. Valid: {valid}."
        ) from None


def validate_access_action(value: str) -> AccessAction:
    try:
        return AccessAction(value)
    except ValueError:
        valid = ", ".join(e.value for e in AccessAction)
        raise IsolationValidationError(
            f"Invalid action '{value}'. Valid: {valid}."
        ) from None


def validate_policy_type(value: str) -> PolicyType:
    try:
        return PolicyType(value)
    except ValueError:
        valid = ", ".join(e.value for e in PolicyType)
        raise IsolationValidationError(
            f"Invalid policy_type '{value}'. Valid: {valid}."
        ) from None


def validate_resource_ids(resource_ids: list[str]) -> None:
    if not resource_ids:
        raise IsolationValidationError("resource_ids must not be empty.")
    for rid in resource_ids:
        if not rid or not rid.strip():
            raise IsolationValidationError("Each resource_id must be non-empty.")


def validate_query_filter(filters: dict[str, object]) -> None:
    if "tenant_id" not in filters:
        raise IsolationValidationError("filters must include 'tenant_id'.")


def validate_policy_update(updates: dict[str, object]) -> dict[str, object]:
    clean: dict[str, object] = {}
    allowed_keys = {
        "name",
        "policy_type",
        "allow_cross_tenant_read",
        "allowed_partner_tenant_ids",
        "is_active",
    }
    for key, value in updates.items():
        if key not in allowed_keys:
            continue
        if key == "policy_type" and value is not None:
            clean[key] = str(validate_policy_type(str(value)))
        elif key == "allowed_partner_tenant_ids" and value is not None:
            clean[key] = [str(UUID(str(tid))) for tid in list(value)]  # type: ignore[arg-type]
        else:
            clean[key] = value
    return clean
