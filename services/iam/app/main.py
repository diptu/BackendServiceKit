from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.db.base import Base
from app.db.session import get_engine  # Your AsyncEngine reference
from app.models import (  # Noqa: F401
    Permission,
    Role,
    RolePermission,
    User,
    UserProfile,
    UserRole,
    UserSocialLink,
)


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

# Wire the API routes under the expected global sub-path
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["System Architecture"])
async def health_check():
    return {"status": "healthy", "service": "iam-engine"}
