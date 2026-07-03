"""Domain exceptions."""

from __future__ import annotations


class NotAnOperatorError(Exception):
    """Caller lacks the platform-admin role required for this operator-only service — 403."""

    def __init__(self, detail: str = "Operator (platform-admin) role required.") -> None:
        super().__init__(detail)
