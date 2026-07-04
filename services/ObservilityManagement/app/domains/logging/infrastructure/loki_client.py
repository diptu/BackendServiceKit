"""Thin async wrapper over Loki's real query API.

No business logic — raw LogQL query in, raw JSON out (or None on any
failure). Query construction lives in `repositories/log_repository.py`,
never here — matches the same layering every domain in this service uses.
"""

from __future__ import annotations

from typing import Any

import httpx


class LokiClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def ready(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/ready")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def query_range(
        self, *, query: str, start_ns: int, end_ns: int, limit: int = 100
    ) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(
                f"{self._base_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_ns,
                    "end": end_ns,
                    "limit": limit,
                    "direction": "backward",
                },
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
