"""Request/response schemas for the logs API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.domain.enums import LogLevel
from app.domain.log_entry import LogEntry
from app.schemas.base import APIModel


class LogEntryResponse(APIModel):
    id: str
    timestamp_ns: str
    level: str | None
    service: str | None
    message: str
    tenant_id: str | None
    user_id: str | None
    trace_id: str | None
    span_id: str | None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_entry(cls, entry: LogEntry, *, log_id: str) -> "LogEntryResponse":
        return cls(
            id=log_id,
            timestamp_ns=entry.timestamp_ns,
            level=entry.level,
            service=entry.service,
            message=entry.message,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            trace_id=entry.trace_id,
            span_id=entry.span_id,
            extra=entry.extra,
        )


class LogSearchResponse(APIModel):
    items: list[LogEntryResponse]
    count: int
    cursor: str | None = None


class LogEntryCreate(APIModel):
    """A single log event submitted via the ingestion escape hatch."""

    level: LogLevel = LogLevel.INFO
    service: str
    message: str
    tenant_id: str | None = None
    user_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LogsBulkCreate(APIModel):
    items: list[LogEntryCreate]


class IngestAcceptedResponse(APIModel):
    accepted: int
