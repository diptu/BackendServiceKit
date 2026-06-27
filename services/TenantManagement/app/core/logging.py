"""Structured JSON logging configuration.

Call ``configure_logging()`` once at service startup (inside the lifespan
handler). Every log record is emitted as a single-line JSON object to stdout,
which is the format expected by log aggregators (Fluent Bit, Logstash, etc.).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class _JSONFormatter(logging.Formatter):
    """Emit one compact JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, debug: bool = False) -> None:
    """Apply JSON structured logging to the root logger.

    Args:
        debug: When ``True``, sets the root level to ``DEBUG`` and enables
               SQLAlchemy statement logging. Use only in development.
    """
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # SQLAlchemy is very chatty at DEBUG — restrict to WARNING unless the
    # service explicitly enables it via debug mode.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if debug else logging.WARNING
    )
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
