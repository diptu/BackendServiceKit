"""Shared test fixtures for UserManagement."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Generator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use SQLite for tests — must be set before app imports trigger engine creation
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_user_management.db")

from app.api.v1.dependencies import get_publisher
from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.infrastructure.messaging.publisher import NullPublisher
from app.main import app

_TEST_DB_URL = "sqlite+aiosqlite:///./test_user_management.db"

_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
_SessionLocal = async_sessionmaker(
    bind=_engine, autoflush=False, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables() -> AsyncIterator[None]:
    import app.models  # noqa: F401  (registers every model on Base.metadata)

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


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _get_db_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    # No real RabbitMQ in tests — publisher calls are exercised via the
    # NullPublisher's no-op path, same as production when the broker is down.
    app.dependency_overrides[get_publisher] = lambda: NullPublisher()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
