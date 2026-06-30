"""Unit tests for resource_validator domain rules."""

from __future__ import annotations

import pytest

from app.domain.exceptions import (
    InvalidResourceIdError,
    InvalidResourceStatusError,
    InvalidResourceTypeError,
)
from app.validators.resource_validator import validate_add_resource


# ── resource_type ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("resource_type", [
    "database_schema",
    "storage_bucket",
    "default_roles",
    "default_permissions",
    "admin_user",
    "workspace",
    "feature_flags",
])
def test_all_known_resource_types_pass(resource_type: str) -> None:
    validate_add_resource(
        resource_type=resource_type,
        resource_id="some-id",
        status="provisioned",
    )


def test_unknown_resource_type_raises() -> None:
    with pytest.raises(InvalidResourceTypeError) as exc_info:
        validate_add_resource(
            resource_type="unknown_type",
            resource_id="some-id",
            status="provisioned",
        )
    assert exc_info.value.resource_type == "unknown_type"
    assert "database_schema" in exc_info.value.valid


def test_capitalised_resource_type_raises() -> None:
    with pytest.raises(InvalidResourceTypeError):
        validate_add_resource(
            resource_type="DATABASE_SCHEMA",
            resource_id="some-id",
            status="provisioned",
        )


# ── resource status ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", ["provisioned", "pending", "failed"])
def test_all_known_resource_statuses_pass(status: str) -> None:
    validate_add_resource(
        resource_type="database_schema",
        resource_id="some-id",
        status=status,
    )


def test_unknown_resource_status_raises() -> None:
    with pytest.raises(InvalidResourceStatusError) as exc_info:
        validate_add_resource(
            resource_type="database_schema",
            resource_id="some-id",
            status="active",
        )
    assert exc_info.value.status == "active"
    assert "provisioned" in exc_info.value.valid


# ── resource_id ───────────────────────────────────────────────────────────────

def test_blank_resource_id_raises() -> None:
    with pytest.raises(InvalidResourceIdError) as exc_info:
        validate_add_resource(
            resource_type="database_schema",
            resource_id="",
            status="provisioned",
        )
    assert "blank" in exc_info.value.reason


def test_whitespace_resource_id_raises() -> None:
    with pytest.raises(InvalidResourceIdError):
        validate_add_resource(
            resource_type="database_schema",
            resource_id="   ",
            status="provisioned",
        )


def test_resource_id_at_max_length_passes() -> None:
    validate_add_resource(
        resource_type="database_schema",
        resource_id="a" * 500,
        status="provisioned",
    )


def test_resource_id_exceeds_max_length_raises() -> None:
    with pytest.raises(InvalidResourceIdError) as exc_info:
        validate_add_resource(
            resource_type="database_schema",
            resource_id="a" * 501,
            status="provisioned",
        )
    assert "500" in exc_info.value.reason
