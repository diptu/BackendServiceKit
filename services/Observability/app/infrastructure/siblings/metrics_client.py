"""Thin async wrapper over MetricsCollection's real system-metrics API.

Response shape assumed from MetricsCollection's own design
(`services/MetricsCollection/` — not currently on disk; see this service's
TODO.md Phase 0) — its `/api/v1/metrics/system` endpoint returns a
passthrough `{"data": {...}}` payload (deliberately loose, per
MetricsCollection's own schema design, to avoid schema drift). Not
re-verified against a running container until MetricsCollection is
rebuilt (Phase 12).
"""

from __future__ import annotations

from typing import Any

import httpx


class MetricsClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def system_metrics(self) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/metrics/system")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None
