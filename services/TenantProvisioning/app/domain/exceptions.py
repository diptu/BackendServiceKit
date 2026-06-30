"""Domain exceptions mapped to HTTP status codes in app/main.py."""

from __future__ import annotations

from uuid import UUID


# ── 404 ───────────────────────────────────────────────────────────────────────

class ProvisioningJobNotFoundError(Exception):
    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Provisioning job {job_id} not found.")
        self.job_id = job_id


class TenantProvisioningNotFoundError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"No provisioning jobs found for tenant {tenant_id}.")
        self.tenant_id = tenant_id


# ── 409 ───────────────────────────────────────────────────────────────────────

class ProvisioningJobAlreadyActiveError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(
            f"An active provisioning job already exists for tenant {tenant_id}."
        )
        self.tenant_id = tenant_id


# ── 422 — domain validation ───────────────────────────────────────────────────

class ProvisioningValidationError(Exception):
    """Base for all domain-level validation failures; mapped to HTTP 422."""


class MetadataTooManyKeysError(ProvisioningValidationError):
    def __init__(self, count: int, maximum: int) -> None:
        super().__init__(
            f"Provisioning metadata exceeds maximum key count: {count} > {maximum}."
        )
        self.count = count
        self.maximum = maximum


class MetadataReservedKeyError(ProvisioningValidationError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Provisioning metadata key '{key}' is reserved.")
        self.key = key


class MetadataKeyTooLongError(ProvisioningValidationError):
    def __init__(self, key: str, max_len: int) -> None:
        super().__init__(
            f"Provisioning metadata key exceeds {max_len} characters: '{key[:32]}'."
        )
        self.key = key
        self.max_len = max_len


class MetadataValueTooLongError(ProvisioningValidationError):
    def __init__(self, key: str, max_len: int) -> None:
        super().__init__(
            f"Provisioning metadata value for key '{key}' exceeds {max_len} characters."
        )
        self.key = key
        self.max_len = max_len


class MetadataBlankKeyError(ProvisioningValidationError):
    def __init__(self) -> None:
        super().__init__("Provisioning metadata keys must not be blank.")


class CannotRetryNonFailedJobError(ProvisioningValidationError):
    def __init__(self, job_id: UUID, current_status: str) -> None:
        super().__init__(
            f"Job {job_id} cannot be retried: status is '{current_status}'. "
            "Only FAILED jobs may be retried."
        )
        self.job_id = job_id
        self.current_status = current_status


class InvalidResourceTypeError(ProvisioningValidationError):
    def __init__(self, resource_type: str, valid: frozenset[str]) -> None:
        super().__init__(
            f"'{resource_type}' is not a valid resource type. "
            f"Valid types: {sorted(valid)}."
        )
        self.resource_type = resource_type
        self.valid = valid


class InvalidResourceStatusError(ProvisioningValidationError):
    def __init__(self, status: str, valid: frozenset[str]) -> None:
        super().__init__(
            f"'{status}' is not a valid resource status. "
            f"Valid statuses: {sorted(valid)}."
        )
        self.status = status
        self.valid = valid


class InvalidResourceIdError(ProvisioningValidationError):
    def __init__(self, resource_id: str, reason: str) -> None:
        super().__init__(f"Invalid resource_id '{resource_id[:64]}': {reason}.")
        self.resource_id = resource_id
        self.reason = reason


class InvalidJobStatusFilterError(ProvisioningValidationError):
    def __init__(self, status: str, valid: frozenset[str]) -> None:
        super().__init__(
            f"'{status}' is not a valid job status filter. "
            f"Valid values: {sorted(valid)}."
        )
        self.status = status
        self.valid = valid
