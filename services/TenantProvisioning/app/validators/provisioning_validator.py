"""Domain-level validation for provisioning job operations.

Pydantic handles field format (types, lengths, regex).
These validators enforce business invariants that require domain knowledge:
- metadata key/value rules and reserved-key protection
- state machine constraints (only FAILED jobs may be retried)
- query filter correctness (status must be a known JobStatus)
"""

from __future__ import annotations

from app.domain.enums import JobStatus
from app.domain.exceptions import (
    CannotRetryNonFailedJobError,
    InvalidJobStatusFilterError,
    MetadataBlankKeyError,
    MetadataKeyTooLongError,
    MetadataReservedKeyError,
    MetadataTooManyKeysError,
    MetadataValueTooLongError,
)
from app.models.provisioning_job import ProvisioningJob

_METADATA_MAX_KEYS: int = 20
_METADATA_MAX_KEY_LEN: int = 128
_METADATA_MAX_VALUE_LEN: int = 1024
_METADATA_RESERVED_KEYS: frozenset[str] = frozenset(
    {"tenant_id", "job_id", "status", "created_at", "updated_at"}
)
_VALID_JOB_STATUSES: frozenset[str] = frozenset(js.value for js in JobStatus)


def validate_start_provisioning(*, metadata: dict[str, str] | None) -> None:
    """Validate domain rules before creating a new provisioning job."""
    if metadata is not None:
        _validate_metadata(metadata)


def validate_can_retry(job: ProvisioningJob) -> None:
    """Enforce that only FAILED jobs may be retried.

    PENDING and RUNNING jobs are blocked by ProvisioningJobAlreadyActiveError (409).
    COMPLETED jobs must be rejected here (422) since re-provisioning a live tenant
    would corrupt its infrastructure.
    """
    if job.status != JobStatus.FAILED.value:
        raise CannotRetryNonFailedJobError(job.id, str(job.status))


def validate_list_jobs_filter(*, status: str | None) -> None:
    """Validate the optional status query filter is a known JobStatus value."""
    if status is not None and status not in _VALID_JOB_STATUSES:
        raise InvalidJobStatusFilterError(status, _VALID_JOB_STATUSES)


def _validate_metadata(metadata: dict[str, str]) -> None:
    if len(metadata) > _METADATA_MAX_KEYS:
        raise MetadataTooManyKeysError(len(metadata), _METADATA_MAX_KEYS)

    for key, value in metadata.items():
        if not key or not key.strip():
            raise MetadataBlankKeyError()
        if key in _METADATA_RESERVED_KEYS:
            raise MetadataReservedKeyError(key)
        if len(key) > _METADATA_MAX_KEY_LEN:
            raise MetadataKeyTooLongError(key, _METADATA_MAX_KEY_LEN)
        if len(value) > _METADATA_MAX_VALUE_LEN:
            raise MetadataValueTooLongError(key, _METADATA_MAX_VALUE_LEN)
