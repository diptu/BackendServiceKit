from collections.abc import AsyncGenerator

from app.core.config import settings
from app.db.session import get_db as _get_db
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

# Standard OAuth2 scheme mapping for automated schema documentation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency provider yielding an active asynchronous SQLAlchemy session matrix.
    Bridges the lower-level DB utilities directly into FastAPI's dependency injection system.
    """
    async for session in _get_db():
        yield session