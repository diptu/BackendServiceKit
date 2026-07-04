"""Thin async httpx wrapper for calling a target's own /health + /ready.

No business logic — raw JSON in, raw JSON out (or None on any failure).
"""

from __future__ import annotations

import time
from typing import Any

import httpx


class TargetProbeResult:
    __slots__ = ("body", "status_code", "latency_ms", "error")

    def __init__(
        self,
        *,
        body: dict[str, Any] | None,
        status_code: int | None,
        latency_ms: float | None,
        error: str | None,
    ) -> None:
        self.body = body
        self.status_code = status_code
        self.latency_ms = latency_ms
        self.error = error

    @property
    def reachable(self) -> bool:
        return self.error is None and self.status_code is not None


class TargetClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def get_health(self, base_url: str) -> TargetProbeResult:
        return await self._get(base_url, "/health")

    async def get_ready(self, base_url: str) -> TargetProbeResult:
        return await self._get(base_url, "/ready")

    async def _get(self, base_url: str, path: str) -> TargetProbeResult:
        url = f"{base_url.rstrip('/')}{path}"
        start = time.monotonic()
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            return TargetProbeResult(body=None, status_code=None, latency_ms=None, error=str(exc))

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        try:
            body = resp.json()
        except ValueError:
            body = None
        return TargetProbeResult(
            body=body if isinstance(body, dict) else None,
            status_code=resp.status_code,
            latency_ms=latency_ms,
            error=None,
        )
