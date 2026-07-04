"""Thin async wrapper over Tenent's real readiness + tenant-list APIs."""

from __future__ import annotations

from typing import Any

import httpx

_MAX_PAGE_SIZE = 100  # Tenent's list endpoint caps limit at 100 (le=100)


class TenentClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    async def get_ready(self) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self._base_url}/ready")
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    async def list_tenants(self) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(
                f"{self._base_url}/api/v1/tenants", params={"limit": _MAX_PAGE_SIZE}
            )
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None
