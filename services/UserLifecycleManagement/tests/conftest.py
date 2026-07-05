"""Shared test fixtures for UserLifecycleManagement."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Generator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use SQLite for tests — must be set before app imports trigger engine creation
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///./test_user_lifecycle_management.db"
)

from app.api.v1.dependencies import get_user_lifecycle_client
from app.domain.enums import LifecycleStatus
from app.domain.exceptions import RemoteUserNotDeletedError, RemoteUserNotFoundError
from app.infrastructure.clients.user_lifecycle_client import (
    RemoteUser,
    UserLifecycleClient,
)
from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app

_TEST_DB_URL = "sqlite+aiosqlite:///./test_user_lifecycle_management.db"

_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
_SessionLocal = async_sessionmaker(
    bind=_engine, autoflush=False, expire_on_commit=False
)


class FakeUserLifecycleClient(UserLifecycleClient):
    """In-memory stand-in for UserManagement — no real HTTP calls leave the
    test process. Tests seed a user's remote state, then exercise this
    service's transitions against it."""

    def __init__(self) -> None:
        self.users: dict[UUID, RemoteUser] = {}

    def seed(
        self,
        user_id: UUID,
        tenant_id: UUID,
        *,
        status: str = "pending",
        deleted_at: datetime | None = None,
        email: str = "test@example.com",
        display_name: str = "Test User",
    ) -> None:
        self.users[user_id] = RemoteUser(
            id=user_id,
            tenant_id=tenant_id,
            email=email,
            display_name=display_name,
            status=status,
            deleted_at=deleted_at,
        )

    async def get_user(self, user_id: UUID, tenant_id: UUID) -> RemoteUser:
        user = self.users.get(user_id)
        if user is None:
            raise RemoteUserNotFoundError(user_id)
        return user

    async def restore_user(self, user_id: UUID, tenant_id: UUID) -> RemoteUser:
        user = self.users.get(user_id)
        if user is None:
            raise RemoteUserNotFoundError(user_id)
        if user.deleted_at is None:
            raise RemoteUserNotDeletedError(user_id)
        user.deleted_at = None
        return user

    async def sync_status(
        self, user_id: UUID, tenant_id: UUID, to_status: LifecycleStatus
    ) -> None:
        """Mirrors the real client's LOCKED-proxies-to-suspended mapping —
        UserManagement has no concept of "locked", only pending/active/
        suspended/deactivated."""
        user = self.users.get(user_id)
        if user is None:
            return
        if to_status == LifecycleStatus.LOCKED:
            user.status = str(LifecycleStatus.SUSPENDED)
        else:
            user.status = str(to_status)


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
def fake_client() -> FakeUserLifecycleClient:
    return FakeUserLifecycleClient()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, fake_client: FakeUserLifecycleClient
) -> AsyncIterator[AsyncClient]:
    async def _get_db_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_user_lifecycle_client] = lambda: fake_client
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
