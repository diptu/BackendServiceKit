"""Shared test fixtures for the Tenant Lifecycle Service."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test_lifecycle.sqlite",
)

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
