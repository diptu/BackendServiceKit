"""Thin async wrapper around Tempo's HTTP query API.

No business logic lives here — raw TraceQL / trace ids in, raw parsed JSON
out. Query construction lives in `app.repositories.trace_repository`; this
module only knows how to talk HTTP to Tempo.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.domain.exceptions import TempoQueryError, TempoUnavailableError

logger = logging.getLogger(__name__)


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

    async def trace_by_id(self, trace_id: str) -> dict[str, Any] | None:
        """Return the raw trace JSON, or None if Tempo has nothing for this id."""
        try:
            resp = await self._client.get(f"{self._base_url}/api/traces/{trace_id}")
        except httpx.TimeoutException as exc:
            raise TempoUnavailableError(f"timeout fetching trace {trace_id}: {exc}") from exc
        except httpx.TransportError as exc:
            raise TempoUnavailableError(
                f"transport error fetching trace {trace_id}: {exc}"
            ) from exc

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise TempoQueryError(resp.status_code, resp.text)
        result: dict[str, Any] = resp.json()
        return result

    async def search(
        self, *, traceql: str, start: int, end: int, limit: int = 20
    ) -> dict[str, Any]:
        return await self._get(
            "/api/search",
            params={"q": traceql, "start": start, "end": end, "limit": limit},
        )

    async def tag_names(self) -> list[str]:
        data = await self._get("/api/search/tags")
        result = data.get("tagNames", [])
        return list(result) if isinstance(result, list) else []

    async def tag_values(self, *, name: str) -> list[str]:
        data = await self._get(f"/api/search/tag/{name}/values")
        result = data.get("tagValues", [])
        return list(result) if isinstance(result, list) else []

    # ------------------------------------------------------------------

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = await self._client.get(f"{self._base_url}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise TempoUnavailableError(f"timeout calling {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise TempoUnavailableError(f"transport error calling {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise TempoQueryError(resp.status_code, resp.text)
        result: dict[str, Any] = resp.json()
        return result
