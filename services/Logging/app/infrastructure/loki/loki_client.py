"""Thin async wrapper around Loki's HTTP API.

No business logic lives here — raw LogQL / label names in, raw parsed JSON
out. Query construction lives in `app.repositories.log_repository`; this
module only knows how to talk HTTP to Loki.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx

from app.domain.exceptions import LokiQueryError, LokiUnavailableError

logger = logging.getLogger(__name__)


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
        self,
        *,
        logql: str,
        start_ns: int,
        end_ns: int,
        limit: int = 100,
        direction: Literal["forward", "backward"] = "backward",
    ) -> dict[str, Any]:
        return await self._get(
            "/loki/api/v1/query_range",
            params={
                "query": logql,
                "start": start_ns,
                "end": end_ns,
                "limit": limit,
                "direction": direction,
            },
        )

    async def query(self, *, logql: str, time_ns: int, limit: int = 100) -> dict[str, Any]:
        return await self._get(
            "/loki/api/v1/query",
            params={"query": logql, "time": time_ns, "limit": limit},
        )

    async def label_values(self, *, label: str) -> list[str]:
        data = await self._get(f"/loki/api/v1/label/{label}/values")
        result = data.get("data", [])
        return list(result) if isinstance(result, list) else []

    async def push(self, *, streams: list[dict[str, Any]]) -> None:
        await self._post("/loki/api/v1/push", json_body={"streams": streams})

    # ------------------------------------------------------------------

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = await self._client.get(f"{self._base_url}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise LokiUnavailableError(f"timeout calling {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise LokiUnavailableError(f"transport error calling {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise LokiQueryError(resp.status_code, resp.text)
        result: dict[str, Any] = resp.json()
        return result

    async def _post(self, path: str, *, json_body: dict[str, Any]) -> None:
        try:
            resp = await self._client.post(f"{self._base_url}{path}", json=json_body)
        except httpx.TimeoutException as exc:
            raise LokiUnavailableError(f"timeout calling {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise LokiUnavailableError(f"transport error calling {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise LokiQueryError(resp.status_code, resp.text)
