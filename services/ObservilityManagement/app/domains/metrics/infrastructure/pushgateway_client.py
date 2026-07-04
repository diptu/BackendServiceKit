"""Thin async wrapper over Pushgateway's real push API (text exposition
format)."""

from __future__ import annotations

import httpx


class PushgatewayClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def push_metric(
        self,
        *,
        job: str,
        metric_name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> bool:
        path_parts = [f"/metrics/job/{job}"]
        for key, val in (labels or {}).items():
            path_parts.append(f"/{key}/{val}")
        url = f"{self._base_url}{''.join(path_parts)}"
        body = f"{metric_name} {value}\n"
        try:
            resp = await self._client.post(url, content=body)
        except httpx.HTTPError:
            return False
        return resp.status_code < 300
