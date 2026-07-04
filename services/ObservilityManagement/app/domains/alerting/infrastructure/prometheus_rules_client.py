"""Thin async wrapper over the two Prometheus endpoints the Alerting domain
needs: `GET /api/v1/rules` (live rule state) and `POST /-/reload` (pick up
a rule file this domain just wrote). Separate from the Metrics domain's
`PrometheusClient` (query-only) since rule management is a distinct
concern, even though both share the same raw backend and httpx client.

Requires --web.enable-lifecycle on the Prometheus server for /-/reload to
work — off by default, verified against a real container while this
domain's design was first built.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.domains.alerting.exceptions import PrometheusError, PrometheusUnavailableError


class PrometheusRulesClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def ready(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/-/ready")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_rules(self) -> dict[str, Any]:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/rules")
        except httpx.TimeoutException as exc:
            raise PrometheusUnavailableError(f"timeout listing rules: {exc}") from exc
        except httpx.TransportError as exc:
            raise PrometheusUnavailableError(f"transport error listing rules: {exc}") from exc

        if resp.status_code >= 400:
            raise PrometheusError(resp.status_code, resp.text)
        result: dict[str, Any] = resp.json()
        return result

    async def reload(self) -> None:
        try:
            resp = await self._client.post(f"{self._base_url}/-/reload")
        except httpx.TimeoutException as exc:
            raise PrometheusUnavailableError(f"timeout reloading: {exc}") from exc
        except httpx.TransportError as exc:
            raise PrometheusUnavailableError(f"transport error reloading: {exc}") from exc

        if resp.status_code >= 400:
            raise PrometheusError(
                resp.status_code,
                f"{resp.text} (is --web.enable-lifecycle set on the Prometheus server?)",
            )
