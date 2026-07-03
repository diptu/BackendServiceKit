"""Structured logging configuration.

Prefers `shared.observability`'s `OTelJSONFormatter` when the `shared/`
package is importable, falling back to a local formatter otherwise —
copied verbatim from the established pattern (`services/Logging/app/core/logging.py`).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

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
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "service": "observability",
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

        _configure(debug=debug, service_name="observability")
        return
    except ImportError:
        pass

    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_FallbackJSONFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
