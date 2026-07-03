"""Thin async wrapper over Logging's real search API.

Response shape assumed from Logging's own design (`services/Logging/` —
not currently on disk; see this service's TODO.md Phase 0). Parsing here
is deliberately defensive since that assumption can't be verified against
a running container until Logging is rebuilt — re-verify field names at
that point, per Phase 12's real-container testing step.
"""

from __future__ import annotations

from typing import Any

import httpx


class LoggingClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def search(
        self, *, query: str, minutes: float = 15.0, limit: int = 100
    ) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(
                f"{self._base_url}/api/v1/logs/search",
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
        body = await self.search(query='{level="error"}', minutes=minutes, limit=1)
        if body is None:
            return None
        items = body.get("items") or body.get("entries") or []
        count = body.get("count")
        if isinstance(count, int):
            return count
        return len(items) if isinstance(items, list) else None
