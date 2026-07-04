"""Thin async wrapper over Tempo's real search + full-trace APIs.

`search` uses Tempo's TraceQL search endpoint (trace summaries only —
no span-level detail). `get_trace` uses Tempo's full-trace endpoint,
which returns the real OTLP-JSON shape (`batches[].resource.attributes`,
`batches[].scopeSpans[].spans[]`) — this is what topology mining actually
needs, closing the assumption flagged in the old Observability service's
TODO.md Implementation Notes (it had assumed a flattened `spans` list on
search results, which Tempo's search endpoint does not actually provide).
"""

from __future__ import annotations

from typing import Any

import httpx


class TempoClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def ready(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/ready")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def search(
        self, *, query: str = "", start_s: int, end_s: int, limit: int = 20
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {"start": start_s, "end": end_s, "limit": limit}
        if query:
            params["q"] = query
        try:
            resp = await self._client.get(f"{self._base_url}/api/search", params=params)
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/traces/{trace_id}")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None
