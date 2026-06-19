from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.api.v1.auth import router as auth_router
from app.api.v1.google_auth import router as google_auth_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.password import router as password_router
from app.api.v1.roles import router as roles_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.seed_rbac import seed_rbac_catalog
from app.db.session import get_engine, get_session_maker
from app.middleware.authorization import JWTContextMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models import (  # Noqa: F401
    Organization,
    OrganizationMember,
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

    # Idempotent: ensures the platform + org RBAC catalogs (roles and their
    # permissions) exist before any protected endpoint is hit.
    async with get_session_maker()() as session:
        await seed_rbac_catalog(session)
    yield


app = FastAPI(
    title="Enterprise RBAC IAM Service",
    description="Stateful dual-token matrix Identity and Access Management layout.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(JWTContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire the API routes under the expected global sub-path
app.include_router(auth_router, prefix="/api/v1")
app.include_router(google_auth_router, prefix="/api/v1")
app.include_router(password_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")


@app.get("/health", tags=["System Architecture"])
async def health_check():
    return {"status": "healthy", "service": "iam-engine"}


@app.get("/metrics", tags=["System Architecture"], include_in_schema=False)
async def metrics() -> Response:
    """
    Prometheus scrape target (see app.core.metrics). Open here for parity
    with /health — in a real deployment, restrict this at the ingress/
    network level rather than behind application auth, since scrapers are
    typically unauthenticated infra clients, not end users.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
