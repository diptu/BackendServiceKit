"""Structured logging configuration.

Prefers `shared.observability`'s `OTelJSONFormatter` (adds trace_id/span_id
from the active span) when the `shared/` package is importable. Falls back
to a local formatter otherwise — `shared/` lives at the repo root and is not
copied into any service's Docker build context today, so importing it can't
be a hard dependency at runtime. Copied from `services/Logging/app/core/logging.py`
verbatim — see that file's docstring for the full reasoning; the same
constraint applies here unchanged.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# Standard LogRecord instance attributes to exclude from the "extra" dump.
# `k not in logging.LogRecord.__dict__` (used elsewhere in this codebase)
# checks class attributes/methods, not instance attributes set in
# `LogRecord.__init__` — it does not actually exclude e.g. `levelname` or
# `pathname`. This is the explicit, correct list.
_STANDARD_RECORD_FIELDS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
        "asctime",
    }
)


class _FallbackJSONFormatter(logging.Formatter):
    """Used only when shared.observability isn't importable (see module docstring)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "service": "distributed-tracing",
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_RECORD_FIELDS and not k.startswith("_")
        }
        if extra:
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(*, debug: bool = False) -> None:
    try:
        from shared.observability.logging.logger import configure_logging as _configure

        _configure(debug=debug, service_name="distributed-tracing")
        return
    except ImportError:
        pass

    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_FallbackJSONFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
