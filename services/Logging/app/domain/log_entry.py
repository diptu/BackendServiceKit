"""Internal representation of a single log line parsed out of a Loki stream."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LogEntry:
    """One log line, reconstructed from a Loki stream + its JSON body.

    `timestamp_ns` is the raw nanosecond-epoch string Loki returns — kept as a
    string throughout to avoid precision loss (it exceeds float64 mantissa
    width for realistic timestamps).
    """

    timestamp_ns: str
    message: str
    level: str | None
    service: str | None
    trace_id: str | None
    span_id: str | None
    tenant_id: str | None
    user_id: str | None
    raw_line: str
    labels: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
