"""Thin async wrapper around Alertmanager's real v2 HTTP API — no business
logic, raw payloads in, raw parsed JSON out."""

from __future__ import annotations

from typing import Any

import httpx

from app.domains.alerting.exceptions import AlertmanagerError, AlertmanagerUnavailableError


class AlertmanagerClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def ready(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/-/healthy")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_alerts(self) -> list[dict[str, Any]]:
        data = await self._get("/api/v2/alerts")
        return data if isinstance(data, list) else []

    async def post_alerts(self, alerts: list[dict[str, Any]]) -> None:
        await self._post("/api/v2/alerts", json_body=alerts)

    async def create_silence(self, *, silence: dict[str, Any]) -> str:
        data = await self._post("/api/v2/silences", json_body=silence)
        if isinstance(data, dict) and "silenceID" in data:
            return str(data["silenceID"])
        raise AlertmanagerError(200, f"unexpected silence response: {data!r}")

    async def _get(self, path: str) -> Any:
        try:
            resp = await self._client.get(f"{self._base_url}{path}")
        except httpx.TimeoutException as exc:
            raise AlertmanagerUnavailableError(f"timeout calling {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise AlertmanagerUnavailableError(f"transport error calling {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise AlertmanagerError(resp.status_code, resp.text)
        return resp.json()

    async def _post(self, path: str, *, json_body: Any) -> Any:
        try:
            resp = await self._client.post(f"{self._base_url}{path}", json=json_body)
        except httpx.TimeoutException as exc:
            raise AlertmanagerUnavailableError(f"timeout calling {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise AlertmanagerUnavailableError(f"transport error calling {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise AlertmanagerError(resp.status_code, resp.text)
        if not resp.content:
            return None
        return resp.json()
