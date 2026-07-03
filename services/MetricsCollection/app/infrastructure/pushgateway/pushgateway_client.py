"""Thin async wrapper around Pushgateway's grouping-key push/delete API.

No metric-shape validation or text-exposition formatting here — that's
`app.services.metric_ingest_service`'s job. This module only knows
Pushgateway's URL scheme (`/metrics/job/<job>[/<label>/<value>...]`) and how
to talk HTTP to it.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from app.domain.exceptions import PushgatewayError, PushgatewayUnavailableError

logger = logging.getLogger(__name__)


def _grouping_path(job: str, labels: dict[str, str]) -> str:
    segments = ["metrics", "job", quote(job, safe="")]
    for key, value in labels.items():
        segments.append(quote(key, safe=""))
        segments.append(quote(value, safe=""))
    return "/" + "/".join(segments)


class PushgatewayClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def push(self, *, job: str, labels: dict[str, str], exposition_text: str) -> None:
        """POST (not PUT) — only replaces metrics with matching names in this
        grouping, leaving any other previously-pushed metric names alone."""
        path = _grouping_path(job, labels)
        try:
            resp = await self._client.post(
                f"{self._base_url}{path}",
                content=exposition_text.encode("utf-8"),
                headers={"Content-Type": "text/plain; version=0.0.4"},
            )
        except httpx.TimeoutException as exc:
            raise PushgatewayUnavailableError(f"timeout pushing to {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise PushgatewayUnavailableError(f"transport error pushing to {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise PushgatewayError(resp.status_code, resp.text)

    async def delete(self, *, job: str, labels: dict[str, str]) -> None:
        path = _grouping_path(job, labels)
        try:
            resp = await self._client.delete(f"{self._base_url}{path}")
        except httpx.TimeoutException as exc:
            raise PushgatewayUnavailableError(f"timeout deleting {path}: {exc}") from exc
        except httpx.TransportError as exc:
            raise PushgatewayUnavailableError(f"transport error deleting {path}: {exc}") from exc

        if resp.status_code >= 400:
            raise PushgatewayError(resp.status_code, resp.text)
