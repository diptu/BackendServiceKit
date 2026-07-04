"""Thin async wrapper over APIGateway's real cross-service status fan-out.

Reuses `GET /api/v1/gateway/status` rather than re-implementing a second
per-upstream health-probing loop — the same reuse decision the original
Monitoring service's design made.
"""

from __future__ import annotations

from typing import Any

import httpx


class GatewayClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def get_gateway_status(self) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/gateway/status")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None
