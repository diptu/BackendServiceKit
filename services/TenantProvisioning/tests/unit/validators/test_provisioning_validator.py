"""Unit tests for provisioning_validator domain rules."""

from __future__ import annotations

import pytest

from app.domain.exceptions import (
    CannotRetryNonFailedJobError,
    InvalidJobStatusFilterError,
    MetadataBlankKeyError,
    MetadataKeyTooLongError,
    MetadataReservedKeyError,
    MetadataTooManyKeysError,
    MetadataValueTooLongError,
)
from app.validators.provisioning_validator import (
    validate_can_retry,
    validate_list_jobs_filter,
    validate_start_provisioning,
)


# ── validate_start_provisioning ───────────────────────────────────────────────

def test_none_metadata_passes() -> None:
    validate_start_provisioning(metadata=None)


def test_empty_metadata_passes() -> None:
    validate_start_provisioning(metadata={})


def test_valid_metadata_passes() -> None:
    validate_start_provisioning(metadata={"region": "us-east-1", "plan": "enterprise"})


def test_too_many_metadata_keys_raises() -> None:
    metadata = {str(i): "v" for i in range(21)}
    with pytest.raises(MetadataTooManyKeysError) as exc_info:
        validate_start_provisioning(metadata=metadata)
    assert exc_info.value.count == 21
    assert exc_info.value.maximum == 20


def test_reserved_key_tenant_id_raises() -> None:
    with pytest.raises(MetadataReservedKeyError) as exc_info:
        validate_start_provisioning(metadata={"tenant_id": "something"})
    assert exc_info.value.key == "tenant_id"


def test_reserved_key_status_raises() -> None:
    with pytest.raises(MetadataReservedKeyError):
        validate_start_provisioning(metadata={"status": "active"})


def test_blank_key_raises() -> None:
    with pytest.raises(MetadataBlankKeyError):
        validate_start_provisioning(metadata={"": "value"})


def test_whitespace_only_key_raises() -> None:
    with pytest.raises(MetadataBlankKeyError):
        validate_start_provisioning(metadata={"   ": "value"})


def test_key_exactly_at_max_length_passes() -> None:
    validate_start_provisioning(metadata={"a" * 128: "value"})


def test_key_exceeds_max_length_raises() -> None:
    with pytest.raises(MetadataKeyTooLongError) as exc_info:
        validate_start_provisioning(metadata={"a" * 129: "value"})
    assert exc_info.value.max_len == 128


def test_value_exactly_at_max_length_passes() -> None:
    validate_start_provisioning(metadata={"key": "v" * 1024})


def test_value_exceeds_max_length_raises() -> None:
    with pytest.raises(MetadataValueTooLongError) as exc_info:
        validate_start_provisioning(metadata={"key": "v" * 1025})
    assert exc_info.value.key == "key"
    assert exc_info.value.max_len == 1024


def test_exactly_20_keys_passes() -> None:
    metadata = {str(i): "v" for i in range(20)}
    validate_start_provisioning(metadata=metadata)


# ── validate_can_retry ────────────────────────────────────────────────────────

def test_failed_job_can_be_retried(make_job) -> None:  # type: ignore[no-untyped-def]
    validate_can_retry(make_job("failed"))  # must not raise


def test_pending_job_cannot_be_retried(make_job) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CannotRetryNonFailedJobError) as exc_info:
        validate_can_retry(make_job("pending"))
    assert exc_info.value.current_status == "pending"


def test_running_job_cannot_be_retried(make_job) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CannotRetryNonFailedJobError) as exc_info:
        validate_can_retry(make_job("running"))
    assert exc_info.value.current_status == "running"


def test_completed_job_cannot_be_retried(make_job) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CannotRetryNonFailedJobError) as exc_info:
        validate_can_retry(make_job("completed"))
    assert exc_info.value.current_status == "completed"


# ── validate_list_jobs_filter ─────────────────────────────────────────────────

def test_none_status_filter_passes() -> None:
    validate_list_jobs_filter(status=None)


@pytest.mark.parametrize("status", ["pending", "running", "completed", "failed"])
def test_all_valid_status_values_pass(status: str) -> None:
    validate_list_jobs_filter(status=status)


def test_unknown_status_filter_raises() -> None:
    with pytest.raises(InvalidJobStatusFilterError) as exc_info:
        validate_list_jobs_filter(status="active")
    assert exc_info.value.status == "active"
    assert "active" not in exc_info.value.valid


def test_capitalised_status_raises() -> None:
    with pytest.raises(InvalidJobStatusFilterError):
        validate_list_jobs_filter(status="PENDING")
