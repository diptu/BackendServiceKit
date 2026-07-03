"""Shared test fixtures for the Distributed Tracing service."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # Bypass the app's lifespan (no real Tempo in unit tests) and inject the
    # httpx client the lifespan would normally create — routes read it via
    # request.app.state.http_client (same pattern as Logging's tests).
    app.state.http_client = httpx.AsyncClient(timeout=5.0)
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await app.state.http_client.aclose()
