"""Shared test fixtures for UserProfileManagement."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Generator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use SQLite for tests — must be set before app imports trigger engine creation
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///./test_user_profile_management.db"
)

from app.api.v1.dependencies import get_user_profile_client
from app.domain.exceptions import RemoteUserNotFoundError
from app.infrastructure.clients.user_profile_client import UserProfileClient
from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app

_TEST_DB_URL = "sqlite+aiosqlite:///./test_user_profile_management.db"

_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
_SessionLocal = async_sessionmaker(
    bind=_engine, autoflush=False, expire_on_commit=False
)


class FakeUserProfileClient(UserProfileClient):
    """In-memory stand-in for UserManagement — no real HTTP calls leave the
    test process. Tests seed known user_ids; anything else 404s, exactly
    like the real client would against a real UserManagement."""

    def __init__(self) -> None:
        self.known_users: set[UUID] = set()

    def seed(self, user_id: UUID) -> None:
        self.known_users.add(user_id)

    async def assert_user_exists(self, user_id: UUID, tenant_id: UUID) -> None:
        if user_id not in self.known_users:
            raise RemoteUserNotFoundError(user_id)


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables() -> AsyncIterator[None]:
    import app.models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with _SessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def fake_client() -> FakeUserProfileClient:
    return FakeUserProfileClient()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, fake_client: FakeUserProfileClient
) -> AsyncIterator[AsyncClient]:
    async def _get_db_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_user_profile_client] = lambda: fake_client
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
