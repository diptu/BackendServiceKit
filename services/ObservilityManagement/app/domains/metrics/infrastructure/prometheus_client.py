"""Thin async wrapper over Prometheus's real query API. Query-only — rule
listing/reload lives in the Alerting domain's own client, since that's a
distinct concern sharing the same raw backend, not this domain's job."""

from __future__ import annotations

from typing import Any

import httpx


class PrometheusClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def ready(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/-/ready")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def instant_query(self, *, query: str) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/query", params={"query": query})
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    async def range_query(
        self, *, query: str, start_s: int, end_s: int, step_s: int = 15
    ) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(
                f"{self._base_url}/api/v1/query_range",
                params={"query": query, "start": start_s, "end": end_s, "step": step_s},
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
