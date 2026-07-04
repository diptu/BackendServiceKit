"""Builds LogQL queries server-side and parses Loki's `query_range`
response — raw LogQL is never exposed to callers directly, only the
structured filters (`service`, `level`, free-text) this domain's own API
accepts. Same rule the original Logging service's design used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    line: str
    labels: dict[str, str] = field(default_factory=dict)


def build_logql_query(
    *, service: str | None = None, level: str | None = None, text: str | None = None
) -> str:
    selector_parts = []
    if service:
        selector_parts.append(f'service="{service}"')
    if level:
        selector_parts.append(f'level="{level}"')
    selector = "{" + ",".join(selector_parts) + "}" if selector_parts else '{job=~".+"}'
    if text:
        escaped = text.replace("`", "'")
        return f"{selector} |= `{escaped}`"
    return selector


def parse_query_range_response(raw: dict[str, Any]) -> list[LogEntry]:
    result = (raw.get("data") or {}).get("result") or []
    if not isinstance(result, list):
        return []

    entries: list[LogEntry] = []
    for stream in result:
        if not isinstance(stream, dict):
            continue
        labels = stream.get("stream") or {}
        values = stream.get("values") or []
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, list) or len(value) != 2:
                continue
            ts_ns, line = value
            entries.append(
                LogEntry(timestamp=_ns_to_iso(ts_ns), line=str(line), labels=dict(labels))
            )

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries


def _ns_to_iso(ts_ns: Any) -> str:
    try:
        seconds = int(ts_ns) / 1_000_000_000
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(seconds, tz=UTC).isoformat()
