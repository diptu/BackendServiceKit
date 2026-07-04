"""Health-domain-specific exceptions."""

from __future__ import annotations


class UnknownServiceError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Unknown service: {name!r}.")
        self.name = name
