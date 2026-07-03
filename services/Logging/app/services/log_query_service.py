"""Read-path business logic: turns validated filters into Loki queries."""

from __future__ import annotations

from typing import Literal

from app.domain.exceptions import LogEntryNotFoundError
from app.domain.log_entry import LogEntry
from app.domain.log_id import decode_log_id, encode_log_id, matches_log_id
from app.infrastructure.loki.loki_client import LokiClient
from app.repositories.log_repository import build_logql, parse_streams

_ID_LOOKUP_WINDOW_NS = 5_000_000_000  # +/- 5s around the encoded timestamp


class LogQueryService:
    def __init__(self, loki_client: LokiClient) -> None:
        self._loki = loki_client

    async def search(
        self,
        *,
        tenant_id: str | None,
        service: str | None = None,
        level: str | None = None,
        user_id: str | None = None,
        query_text: str | None = None,
        start_ns: int,
        end_ns: int,
        limit: int = 100,
        direction: Literal["forward", "backward"] = "backward",
    ) -> list[LogEntry]:
        logql = build_logql(
            service=service,
            level=level,
            tenant_id=tenant_id,
            user_id=user_id,
            query_text=query_text,
        )
        data = await self._loki.query_range(
            logql=logql, start_ns=start_ns, end_ns=end_ns, limit=limit, direction=direction
        )
        return parse_streams(data)

    async def get_by_id(self, log_id: str) -> tuple[LogEntry, str]:
        """Return the entry the id encodes plus the id itself (unchanged)."""
        payload = decode_log_id(log_id)
        ts_ns = int(str(payload["ts"]))
        logql = build_logql(service=payload.get("s"), level=payload.get("l"))
        data = await self._loki.query_range(
            logql=logql,
            start_ns=ts_ns - _ID_LOOKUP_WINDOW_NS,
            end_ns=ts_ns + _ID_LOOKUP_WINDOW_NS,
            limit=200,
        )
        for entry in parse_streams(data):
            if matches_log_id(payload, entry.raw_line):
                return entry, log_id
        raise LogEntryNotFoundError(
            f"No log entry matches id {log_id!r} (outside window or purged)."
        )

    @staticmethod
    def encode_id_for(entry: LogEntry) -> str:
        return encode_log_id(
            service=entry.service,
            level=entry.level,
            timestamp_ns=entry.timestamp_ns,
            raw_line=entry.raw_line,
        )
