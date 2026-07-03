"""Internal representation of a span/trace, reshaped from Tempo's OTLP-JSON response.

Unlike Logging's `LogEntry` (which needed a synthetic id — see
`services/Logging/app/domain/log_id.py`), a `trace_id` is already a stable,
real, addressable identifier in Tempo — no synthetic id scheme is needed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Span:
    span_id: str
    parent_span_id: str | None
    name: str
    service: str | None
    start_ns: int
    end_ns: int
    status: str  # "ok" | "error" | "unset"
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ns(self) -> int:
        return max(self.end_ns - self.start_ns, 0)


@dataclass(frozen=True)
class Trace:
    trace_id: str
    spans: list[Span]

    @property
    def root_span(self) -> Span | None:
        if not self.spans:
            return None
        span_ids = {s.span_id for s in self.spans}
        for s in self.spans:
            if not s.parent_span_id or s.parent_span_id not in span_ids:
                return s
        return self.spans[0]

    @property
    def start_ns(self) -> int:
        return min((s.start_ns for s in self.spans), default=0)

    @property
    def end_ns(self) -> int:
        return max((s.end_ns for s in self.spans), default=0)

    @property
    def duration_ns(self) -> int:
        return max(self.end_ns - self.start_ns, 0)

    @property
    def service_names(self) -> set[str]:
        return {s.service for s in self.spans if s.service}


@dataclass(frozen=True)
class TraceSummary:
    """One row of a Tempo `/api/search` result — not a full span tree."""

    trace_id: str
    root_service_name: str | None
    root_trace_name: str | None
    start_ns: int
    duration_ms: float
