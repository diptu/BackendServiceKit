"""Request/response schemas for the Logs domain."""

from __future__ import annotations

from pydantic import Field

from app.core.schema_base import APIModel
from app.domains.logging.repositories.log_repository import LogEntry


class LogEntryResponse(APIModel):
    timestamp: str
    line: str
    labels: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, entry: LogEntry) -> "LogEntryResponse":
        return cls(timestamp=entry.timestamp, line=entry.line, labels=entry.labels)


class LogSearchResponse(APIModel):
    items: list[LogEntryResponse]
    count: int
