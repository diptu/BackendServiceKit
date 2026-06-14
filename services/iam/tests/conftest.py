# tests/conftest.py
import pytest
from anyio import Path
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app as app_instance
from app.models.user import User  # noqa

# Generate a distinct test database file name for this session execution
TEST_DB_FILE = "test_db.sqlite"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"


@pytest.fixture(scope="session")
def anyio_backend():
    """Tells pytest to evaluate session-scoped async fixtures using asyncio."""
    return "asyncio"


@pytest.fixture(scope="session")
async def test_db():
    """
    Session-scoped database controller fixture.
    Setup runs once before any tests start. Teardown runs strictly
    after all tests in the session are completed.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    testing_session_local = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        # Now SQLAlchemy knows about the `users` table because User was imported above
        await conn.run_sync(Base.metadata.create_all)

    yield testing_session_local

    # Teardown Phase (Executes only after the test session is completed)
    await engine.dispose()
    test_db_path = Path(TEST_DB_FILE)

    if await test_db_path.exists():
        try:
            await test_db_path.unlink()
        except PermissionError:
            await test_db_path.unlink()


@pytest.fixture(scope="session")
def app(test_db):
    """Provides application instance with test database dependency overrides."""

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
