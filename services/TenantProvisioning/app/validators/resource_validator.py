"""Domain-level validation for provisioning resource registration.

Pydantic handles field lengths and types.
These validators enforce domain invariants:
- resource_type must be a known ResourceType value
- status must be a known ResourceStatus value
- resource_id must not be blank (distinct from the length check in the schema)
"""

from __future__ import annotations

from app.domain.enums import ResourceStatus, ResourceType
from app.domain.exceptions import (
    InvalidResourceIdError,
    InvalidResourceStatusError,
    InvalidResourceTypeError,
)

_VALID_RESOURCE_TYPES: frozenset[str] = frozenset(rt.value for rt in ResourceType)
_VALID_RESOURCE_STATUSES: frozenset[str] = frozenset(rs.value for rs in ResourceStatus)
_RESOURCE_ID_MAX_LEN: int = 500


def validate_add_resource(
    *,
    resource_type: str,
    resource_id: str,
    status: str,
) -> None:
    """Validate domain rules for manual resource registration."""
    _validate_resource_type(resource_type)
    _validate_resource_status(status)
    _validate_resource_id(resource_id)


def _validate_resource_type(resource_type: str) -> None:
    if resource_type not in _VALID_RESOURCE_TYPES:
        raise InvalidResourceTypeError(resource_type, _VALID_RESOURCE_TYPES)


def _validate_resource_status(status: str) -> None:
    if status not in _VALID_RESOURCE_STATUSES:
        raise InvalidResourceStatusError(status, _VALID_RESOURCE_STATUSES)


def _validate_resource_id(resource_id: str) -> None:
    if not resource_id or not resource_id.strip():
        raise InvalidResourceIdError(resource_id, "must not be blank")
    if len(resource_id) > _RESOURCE_ID_MAX_LEN:
        raise InvalidResourceIdError(
            resource_id,
            f"must not exceed {_RESOURCE_ID_MAX_LEN} characters",
        )
