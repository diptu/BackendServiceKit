"""JSON log formatter that injects trace_id and span_id from the active OTel span."""

from __future__ import annotations

import json
import logging
import os
from typing import Any


class OTelJSONFormatter(logging.Formatter):
    """Emit one compact JSON object per log record, including OTel trace context."""

    def format(self, record: logging.LogRecord) -> str:
        trace_id: str | None = None
        span_id: str | None = None
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")
        except Exception:
            pass

        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "service": os.getenv("OTEL_SERVICE_NAME", "unknown"),
            "trace_id": trace_id,
            "span_id": span_id,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__ and not k.startswith("_")
            and k not in ("message", "asctime", "msg", "args")
        }
        if extra:
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False, default=str)
