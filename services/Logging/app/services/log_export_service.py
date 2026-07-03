"""Streaming NDJSON export — synchronous, no worker infra (see TODO.md Phase 7)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from app.services.log_query_service import LogQueryService

_PAGE_SIZE = 500
_MAX_PAGES = 200  # hard safety cap: 100k lines per export


class LogExportService:
    def __init__(self, query_service: LogQueryService) -> None:
        self._query_service = query_service

    async def export_ndjson(
        self,
        *,
        tenant_id: str | None,
        service: str | None,
        level: str | None,
        user_id: str | None,
        query_text: str | None,
        start_ns: int,
        end_ns: int,
    ) -> AsyncIterator[bytes]:
        cursor_end = end_ns
        for _ in range(_MAX_PAGES):
            entries = await self._query_service.search(
                tenant_id=tenant_id,
                service=service,
                level=level,
                user_id=user_id,
                query_text=query_text,
                start_ns=start_ns,
                end_ns=cursor_end,
                limit=_PAGE_SIZE,
                direction="backward",
            )
            if not entries:
                return
            for entry in entries:
                yield (
                    json.dumps(
                        {
                            "timestamp_ns": entry.timestamp_ns,
                            "level": entry.level,
                            "service": entry.service,
                            "message": entry.message,
                            "tenant_id": entry.tenant_id,
                            "user_id": entry.user_id,
                            "trace_id": entry.trace_id,
                            **entry.extra,
                        },
                        default=str,
                    )
                    + "\n"
                ).encode("utf-8")
            if len(entries) < _PAGE_SIZE:
                return
            # Next page: strictly before the oldest line we just yielded.
            oldest_ns = int(entries[-1].timestamp_ns)
            if oldest_ns <= start_ns:
                return
            cursor_end = oldest_ns - 1
