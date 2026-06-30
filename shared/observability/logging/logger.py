"""Structured logging setup — OTel-aware JSON formatter on root logger."""

from __future__ import annotations

import logging
import sys

from shared.observability.logging.json_formatter import OTelJSONFormatter


def configure_logging(*, debug: bool = False, service_name: str = "unknown") -> None:
    """Install OTelJSONFormatter on the root logger.

    Drop-in replacement for per-service configure_logging functions. Call once
    at application startup, before the OTel tracer is configured (the formatter
    gracefully returns None trace_id/span_id if no active span exists yet).
    """
    import os

    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)

    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(OTelJSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    for noisy in ("uvicorn.access", "uvicorn.error", "celery", "aio_pika", "httpx", "sqlalchemy"):
        logging.getLogger(noisy).setLevel(logging.WARNING if not debug else logging.DEBUG)
