"""Thin async wrapper around Prometheus's HTTP query API.

No business logic lives here — raw PromQL / label names in, raw parsed JSON
out. Query construction lives in `app.repositories.metric_repository`; this
module only knows how to talk HTTP to Prometheus.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.domain.exceptions import PrometheusQueryError, PrometheusUnavailableError

logger = logging.getLogger(__name__)


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

    async def instant_query(self, *, promql: str, time_s: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"query": promql}
        if time_s is not None:
            params["time"] = time_s
        return await self._get("/api/v1/query", params=params)

    async def range_query(
        self, *, promql: str, start_s: int, end_s: int, step: str = "60s"
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/query_range",
            params={"query": promql, "start": start_s, "end": end_s, "step": step},
        )

    async def label_values(self, *, name: str) -> list[str]:
        data = await self._get(f"/api/v1/label/{name}/values")
        result = data.get("data", [])
        return list(result) if isinstance(result, list) else []

    async def metric_names(self) -> list[str]:
        return await self.label_values(name="__name__")

    # ------------------------------------------------------------------

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = await self._client.get(f"{self._base_url}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise PrometheusUnavailableError(f"timeout calling {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise PrometheusUnavailableError(f"transport error calling {path}: {exc}") from exc

        if resp.status_code >= 500:
            raise PrometheusUnavailableError(f"{resp.status_code} calling {path}")

        try:
            body: dict[str, Any] = resp.json()
        except ValueError as exc:
            raise PrometheusQueryError(f"non-JSON response from {path}: {exc}") from exc

        if resp.status_code >= 400 or body.get("status") == "error":
            error_detail = body.get("error") or resp.text
            raise PrometheusQueryError(f"{path}: {error_detail}")

        return body
