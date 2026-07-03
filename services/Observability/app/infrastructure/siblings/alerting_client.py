"""Thin async wrapper over Alerting's real alert-list API.

Unlike the other sibling clients in this module, this shape is not a
guess — `GET /api/v1/alerts` returns `{"items": [...], "count": N}` where
each item has `fingerprint`, `labels`, `annotations`, `starts_at`,
`ends_at`, `state`, `silenced_by`, `inhibited_by`, `receivers` (see
`services/Alerting/app/schemas/alert.py`'s `AlertResponse` — not currently
on disk, but this exact shape is what was built and verified against a
real Alertmanager earlier in this project's history; see this service's
TODO.md Phase 0).
"""

from __future__ import annotations

from typing import Any

import httpx


class AlertingClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def list_alerts(self) -> list[dict[str, Any]] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/api/v1/alerts")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        if not isinstance(body, dict):
            return None
        items = body.get("items")
        return items if isinstance(items, list) else None
