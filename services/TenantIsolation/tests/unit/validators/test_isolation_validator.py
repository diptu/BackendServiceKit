"""Unit tests for isolation validators."""

from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidQueryFilterError, IsolationValidationError
from app.validators.isolation_validator import (
    validate_access_action,
    validate_policy_update,
    validate_query_filter,
    validate_resource_ids,
    validate_resource_type,
)


def test_validate_resource_ids_valid() -> None:
    validate_resource_ids(["abc", "def-123"])


def test_validate_resource_ids_blank() -> None:
    with pytest.raises(IsolationValidationError, match="blank"):
        validate_resource_ids([""])


def test_validate_resource_ids_whitespace() -> None:
    with pytest.raises(IsolationValidationError, match="blank"):
        validate_resource_ids(["   "])


def test_validate_resource_ids_too_long() -> None:
    with pytest.raises(IsolationValidationError, match="maximum length"):
        validate_resource_ids(["x" * 501])


def test_validate_resource_type_valid() -> None:
    validate_resource_type("document")
    validate_resource_type("workspace")
    validate_resource_type("user")


def test_validate_resource_type_invalid() -> None:
    with pytest.raises(IsolationValidationError, match="not a valid resource type"):
        validate_resource_type("foobar")


def test_validate_access_action_valid() -> None:
    validate_access_action("read")
    validate_access_action("write")
    validate_access_action("delete")
    validate_access_action("admin")


def test_validate_access_action_invalid() -> None:
    with pytest.raises(IsolationValidationError, match="not a valid access action"):
        validate_access_action("execute")


def test_validate_query_filter_valid() -> None:
    validate_query_filter({"tenant_id": "abc", "other": "val"})


def test_validate_query_filter_missing_tenant_id() -> None:
    with pytest.raises(InvalidQueryFilterError, match="tenant_id"):
        validate_query_filter({"other": "val"})


def test_validate_policy_update_valid_uuids() -> None:
    from uuid import uuid4
    validate_policy_update([str(uuid4()), str(uuid4())])


def test_validate_policy_update_none() -> None:
    validate_policy_update(None)


def test_validate_policy_update_invalid_uuid() -> None:
    with pytest.raises(IsolationValidationError, match="invalid UUID"):
        validate_policy_update(["not-a-uuid"])
