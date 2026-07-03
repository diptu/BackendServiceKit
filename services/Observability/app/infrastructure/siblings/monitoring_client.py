"""Thin async wrapper over Monitoring's real summary API.

Only the summary endpoint is used here, per TODO.md Decision #4 — this
service needs the topology-level headline status, not Monitoring's full
dashboard (composing that would blur the line between the two services'
responsibilities). Shape assumed from Monitoring's own design
(`services/Monitoring/` — not currently on disk; see this service's
TODO.md Phase 0).
"""

from __future__ import annotations

from typing import Any

import httpx


class MonitoringClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def summary(self) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/monitoring/summary")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None
