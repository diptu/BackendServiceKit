"""Translates domain-level filters into LogQL and parses Loki's response back.

This is the only place LogQL syntax is constructed — no other module should
build a query string by hand. Keeping it isolated here is what makes the
`tests/unit/test_log_repository.py` "given filters -> expected LogQL" tests
possible without a running Loki.

Label vocabulary (must match `services/Logging/promtail/promtail-config.yaml`):
    Indexed labels (fast, used in the stream selector): `service`, `level`,
    `container`, `image`, `job`, `trace_id`.
    Everything else the JSON formatter emits (`tenant_id`, `user_id`, `logger`,
    `span_id`, ...) lives in the line body and is only reachable via a
    `| json` parser stage + field filter — never as a label matcher.
"""

from __future__ import annotations

from typing import Any

from app.domain.exceptions import InvalidLogQLError
from app.domain.log_entry import LogEntry

_RESERVED_EXTRA_KEYS = frozenset(
    {"time", "level", "logger", "service", "trace_id", "span_id", "message", "tenant_id", "user_id"}
)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_logql(
    *,
    service: str | None = None,
    level: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    query_text: str | None = None,
) -> str:
    """Build a LogQL selector for the given filters.

    `service`/`level` become label matchers (cheap, indexed). `tenant_id`/
    `user_id` are filtered post-parse via `| json` since they are not
    promoted labels. `query_text` is applied as a raw line-contains filter
    before JSON parsing, since that's the cheapest possible filter in Loki.
    """
    matchers = []
    if service:
        matchers.append(f'service="{_escape(service)}"')
    if level:
        matchers.append(f'level="{_escape(level.upper())}"')
    if not matchers:
        # Loki requires at least one label matcher in the stream selector.
        matchers.append('service=~".+"')
    selector = "{" + ", ".join(matchers) + "}"

    stages = [selector]
    if query_text:
        if '"' in query_text:
            raise InvalidLogQLError("Free-text search may not contain a double quote.")
        stages.append(f'|= "{query_text}"')

    needs_json = bool(tenant_id or user_id)
    if needs_json:
        stages.append("| json")
        if tenant_id:
            stages.append(f'| tenant_id="{_escape(tenant_id)}"')
        if user_id:
            stages.append(f'| user_id="{_escape(user_id)}"')

    return " ".join(stages)


def parse_streams(data: dict[str, Any]) -> list[LogEntry]:
    """Parse a Loki `query`/`query_range` response body into `LogEntry` objects."""
    result = data.get("data", {}).get("result", [])
    entries: list[LogEntry] = []
    for stream in result:
        labels: dict[str, str] = stream.get("stream", {})
        for ts_ns, raw_line in stream.get("values", []):
            entries.append(_parse_line(labels, ts_ns, raw_line))
    entries.sort(key=lambda e: e.timestamp_ns, reverse=True)
    return entries


def _parse_line(labels: dict[str, str], timestamp_ns: str, raw_line: str) -> LogEntry:
    import json as _json

    body: dict[str, Any] = {}
    try:
        parsed = _json.loads(raw_line)
        if isinstance(parsed, dict):
            body = parsed
    except ValueError:
        pass

    extra = {k: v for k, v in body.items() if k not in _RESERVED_EXTRA_KEYS}

    return LogEntry(
        timestamp_ns=timestamp_ns,
        message=str(body.get("message", raw_line)),
        level=body.get("level") or labels.get("level"),
        service=body.get("service") or labels.get("service"),
        trace_id=body.get("trace_id") or labels.get("trace_id"),
        span_id=body.get("span_id"),
        tenant_id=body.get("tenant_id"),
        user_id=body.get("user_id"),
        raw_line=raw_line,
        labels=dict(labels),
        extra=extra,
    )
