from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.google_auth import router as google_auth_router
from app.api.v1.password import router as password_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import get_engine  # Your AsyncEngine reference
from app.middleware.logging import RequestLoggingMiddleware
from app.models import (  # Noqa: F401
    PasswordResetToken,
    Permission,
    Role,
    RolePermission,
    User,
    UserProfile,
    UserRole,
    UserSocialLink,
)

configure_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # DDL Construction Logic Execution at system boot time
    async with get_engine().begin() as conn:
        # Automatically detects missing tables and builds them on-the-fly
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Enterprise RBAC IAM Service",
    description="Stateful dual-token matrix Identity and Access Management layout.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

# Wire the API routes under the expected global sub-path
app.include_router(auth_router, prefix="/api/v1")
app.include_router(google_auth_router, prefix="/api/v1")
app.include_router(password_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


@app.get("/health", tags=["System Architecture"])
async def health_check():
    return {"status": "healthy", "service": "iam-engine"}
