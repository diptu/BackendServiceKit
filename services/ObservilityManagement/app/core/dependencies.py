"""Shared FastAPI dependency getters used across every domain — one shared
`httpx.AsyncClient` for all outbound calls (tier-1 backends and external
services alike), built once in main.py's lifespan. See TODO.md Decision #3."""

from __future__ import annotations

import httpx
from fastapi import Request


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient = request.app.state.http_client
    return client
