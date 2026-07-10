"""FastAPI shared dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import AccessTokenInvalidError, SsoNotConfiguredError
from app.infrastructure.database.dependencies import get_db
from app.services.auth_service import AuthService
from app.services.mfa_service import MfaService
from app.services.oauth_service import OAuthService
from app.services.oidc_client import HttpxOidcClient, load_provider_config
from app.services.sso_service import SsoService
from app.services.token_service import AccessTokenClaims, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(db)


async def get_current_subject(
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
) -> AccessTokenClaims:
    """Decode the Authorization: Bearer access token. Requires the caller to
    already hold a valid, non-expired access token issued by /auth/login or
    /auth/refresh — used to gate endpoints that act on "the current user"
    (change-password, logout-all, session listing/revocation)."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <access_token> is required.",
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except AccessTokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    if claims["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tenant does not match X-Tenant-ID.",
        )
    return claims


async def get_mfa_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MfaService:
    return MfaService(db)


async def get_oauth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthService:
    return OAuthService(db)


async def get_sso_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SsoService:
    """Wires the real httpx-backed OIDC client from provider config. Tests
    override this dependency to inject a fake client. Returns 503 if no IdP
    is configured rather than surfacing an internal error."""
    try:
        config = load_provider_config()
    except SsoNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return SsoService(db, HttpxOidcClient(config))


DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentSubjectDep = Annotated[AccessTokenClaims, Depends(get_current_subject)]
MfaServiceDep = Annotated[MfaService, Depends(get_mfa_service)]
OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
SsoServiceDep = Annotated[SsoService, Depends(get_sso_service)]
