"""Domain exceptions."""

from __future__ import annotations


class LokiUnavailableError(Exception):
    """Loki did not respond (connection/timeout) — 503."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Loki is unavailable: {detail}")
        self.detail = detail


class LokiQueryError(Exception):
    """Loki responded with a non-2xx status — 502."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Loki query failed ({status_code}): {detail}")
        self.status_code = status_code
        self.detail = detail


class InvalidLogQLError(Exception):
    """Caller-supplied filters could not be translated into a valid query — 422."""


class MissingTenantScopeError(Exception):
    """Caller has no tenant_id and is not platform-admin — 403."""

    def __init__(self, detail: str = "Request is missing a tenant scope.") -> None:
        super().__init__(detail)


class CrossTenantAccessError(Exception):
    """Caller's tenant does not match the requested tenant_id — 403."""

    def __init__(self, detail: str = "Cannot access another tenant's logs.") -> None:
        super().__init__(detail)


class InvalidLogIdError(Exception):
    """The `{id}` path parameter could not be decoded — 404."""


class LogEntryNotFoundError(Exception):
    """No line in Loki matched the decoded id within its time window — 404."""


class BulkIngestLimitExceededError(Exception):
    """POST /logs/bulk payload exceeds the configured max item count — 422."""

    def __init__(self, count: int, limit: int) -> None:
        super().__init__(f"Bulk payload has {count} items; limit is {limit}.")
        self.count = count
        self.limit = limit
