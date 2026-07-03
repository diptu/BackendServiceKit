"""Thin async wrapper over HealthCheck's real fleet health API.

Also not a guess — `GET /health/live` returns
`{"items": [{"service", "reachable", "version"}], "count": N}` and
`GET /health/dependencies` returns
`{"overall_status": ..., "services": [ServiceHealthResponse...]}` (see
`services/HealthCheck/app/schemas/health.py` — not currently on disk, but
this exact shape is what was built and verified against real containers
earlier in this project's history; see this service's TODO.md Phase 0).
"""

from __future__ import annotations

from typing import Any

import httpx


class HealthClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def liveness(self) -> list[dict[str, Any]] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/health/live")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        if not isinstance(body, dict):
            return None
        items = body.get("items")
        return items if isinstance(items, list) else None

    async def dependencies(self) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/health/dependencies")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None
