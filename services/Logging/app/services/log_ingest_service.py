"""Ingestion escape hatch — for emitters that cannot log to stdout under promtail.

Internal services (Tenent, APIGateway, ...) already ship logs to Loki via
stdout -> Docker -> promtail with zero code here. This path exists only for
emitters promtail cannot reach: browser/mobile clients, third-party webhook
receivers, serverless functions.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from app.domain.exceptions import BulkIngestLimitExceededError
from app.infrastructure.loki.loki_client import LokiClient
from app.schemas.log import LogEntryCreate

logger = logging.getLogger(__name__)


def _get_trace_context() -> dict[str, str | None]:
    # shared/ is not copied into this service's Docker build context (see
    # services/Logging/TODO.md) — best-effort only, same allowance
    # Tenent/APIGateway make for shared.observability.tracing.
    try:
        from shared.observability.logging.correlation import get_trace_context

        result: dict[str, str | None] = get_trace_context()
        return result
    except ImportError:
        return {"trace_id": None, "span_id": None}


class LogIngestService:
    def __init__(self, loki_client: LokiClient, *, max_bulk_items: int) -> None:
        self._loki = loki_client
        self._max_bulk_items = max_bulk_items

    async def ingest_one(self, item: LogEntryCreate) -> int:
        return await self.ingest_bulk([item])

    async def ingest_bulk(self, items: list[LogEntryCreate]) -> int:
        if len(items) > self._max_bulk_items:
            raise BulkIngestLimitExceededError(len(items), self._max_bulk_items)

        streams_by_key: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
        for item in items:
            ts_ns = str(time.time_ns())
            trace_ctx = _get_trace_context()
            body = {
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                "level": item.level.value,
                "logger": "logging-service.ingest",
                "service": item.service,
                "trace_id": trace_ctx["trace_id"],
                "span_id": trace_ctx["span_id"],
                "message": item.message,
                "tenant_id": item.tenant_id,
                "user_id": item.user_id,
                **item.extra,
            }
            line = json.dumps(body, ensure_ascii=False, default=str)
            streams_by_key[(item.service, item.level.value)].append([ts_ns, line])

        streams = [
            {"stream": {"service": svc, "level": lvl, "job": "logging-ingest"}, "values": values}
            for (svc, lvl), values in streams_by_key.items()
        ]
        await self._loki.push(streams=streams)
        logger.info("logs_ingested", extra={"count": len(items)})
        return len(items)
