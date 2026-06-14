import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app as app_instance

# Ensure your User model (and all other models) are imported here!

# Use shared cache in-memory sqlite to allow multiple connections to see the same tables
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"


@pytest.fixture(scope="session")
def anyio_backend():
    """Forces pytest-anyio to use the asyncio backend."""
    return "asyncio"


@pytest.fixture
async def test_db():
    """
    Function-scoped database fixture. Provides a completely pristine
    database environment for every single test.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    testing_session_local = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    # Keep a reference to the underlying connection open so the
    # in-memory database isn't wiped instantly between session blocks.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield testing_session_local

    # Clean up cleanly without worrying about async file systems
    await engine.dispose()


@pytest.fixture
def app(test_db):
    """Overrides the fastAPI dependency injection per-test."""

    async def _override_get_db():
        async with test_db() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app_instance.dependency_overrides[get_db] = _override_get_db
    yield app_instance
    app_instance.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """Provides an isolated HTTPX Client to individual test instances."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
