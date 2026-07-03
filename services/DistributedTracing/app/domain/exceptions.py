"""Domain exceptions."""

from __future__ import annotations


class TempoUnavailableError(Exception):
    """Tempo did not respond (connection/timeout) — 503."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Tempo is unavailable: {detail}")
        self.detail = detail


class TempoQueryError(Exception):
    """Tempo responded with a non-2xx status — 502."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Tempo query failed ({status_code}): {detail}")
        self.status_code = status_code
        self.detail = detail


class InvalidTraceQLError(Exception):
    """Caller-supplied filters could not be translated into a valid query — 422."""


class TraceNotFoundError(Exception):
    """No trace found for the given id — 404."""


class NotAnOperatorError(Exception):
    """Caller lacks the platform-admin role required for this operator-only service — 403."""

    def __init__(self, detail: str = "Operator (platform-admin) role required.") -> None:
        super().__init__(detail)
