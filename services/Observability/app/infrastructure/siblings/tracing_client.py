"""Thin async wrapper over DistributedTracing's real search API.

Response shape assumed from DistributedTracing's own design
(`services/DistributedTracing/` — not currently on disk; see this
service's TODO.md Phase 0). Each trace item is assumed to carry a `spans`
list with `service_name`/`span_id`/`parent_span_id` — real OpenTelemetry/
Tempo conventions, but unverified against a running container until
DistributedTracing is rebuilt (Phase 12).
"""

from __future__ import annotations

from typing import Any

import httpx


class TracingClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def search(
        self, *, query: str = "", minutes: float = 15.0, limit: int = 100
    ) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(
                f"{self._base_url}/api/v1/traces/search",
                params={"query": query, "minutes": minutes, "limit": limit},
            )
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        body = await self.search(query="status=error", minutes=minutes, limit=1)
        if body is None:
            return None
        items = body.get("items") or body.get("traces") or []
        count = body.get("count")
        if isinstance(count, int):
            return count
        return len(items) if isinstance(items, list) else None

    async def recent_traces(
        self, *, minutes: float = 15.0, limit: int = 50
    ) -> list[dict[str, Any]] | None:
        """Raw trace items (each expected to carry a `spans` list) — used
        by `topology_repository.py` to mine real service-call edges."""
        body = await self.search(minutes=minutes, limit=limit)
        if body is None:
            return None
        items = body.get("items") or body.get("traces") or []
        return items if isinstance(items, list) else None
