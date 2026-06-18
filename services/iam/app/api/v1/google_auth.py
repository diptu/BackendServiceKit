"""
Google OAuth2 OIDC endpoints.

Routes
------
GET  /auth/google/login     — generate authorization URL (SPA-friendly JSON response)
GET  /auth/google/callback  — receive code + state from Google, mint local JWT pair
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import _set_refresh_cookie
from app.api.v1.dependencies import get_async_db
from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.google_auth import GoogleLoginInitResponse
from app.schemas.user import TokenMatrixResponse
from app.services.auth import AuthService
from app.services.google_oauth import GoogleOAuthService

router = APIRouter(
    prefix="/auth/google",
    tags=["Federated Identity — Google OAuth2"],
)

_audit_logger = AuditLogger()


def _get_google_service(
    db: AsyncSession = Depends(get_async_db),
) -> GoogleOAuthService:
    return GoogleOAuthService(
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
    )


def _get_auth_service(
    db: AsyncSession = Depends(get_async_db),
) -> AuthService:
    return AuthService(
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
        audit_logger=_audit_logger,
    )


# ---------------------------------------------------------------------------
# Step 1 — initiate login (SPA / mobile-friendly)
# ---------------------------------------------------------------------------


@router.get(
    "/login",
    response_model=GoogleLoginInitResponse,
    summary="Initiate Google OAuth2 login — returns the consent URL",
)
async def google_login(
    google: Annotated[GoogleOAuthService, Depends(_get_google_service)],
) -> GoogleLoginInitResponse:
    """
    Generate a Google consent-screen URL with a CSRF state token embedded.

    The client (SPA / mobile app) should redirect the user to
    ``authorization_url``.  After the user grants consent, Google redirects
    back to ``/auth/google/callback`` with ``code`` and ``state`` query params.
    """
    url = google.generate_auth_url()
    return GoogleLoginInitResponse(authorization_url=url)


# ---------------------------------------------------------------------------
# Step 2 — callback (Google redirects here after consent)
# ---------------------------------------------------------------------------


@router.get(
    "/callback",
    response_model=TokenMatrixResponse,
    summary="Google OAuth2 callback — exchange code for local JWT pair",
)
async def google_callback(
    request: Request,
    response: Response,
    google: Annotated[GoogleOAuthService, Depends(_get_google_service)],
    auth: Annotated[AuthService, Depends(_get_auth_service)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> TokenMatrixResponse:
    """
    Handle Google's authorization callback.

    1. Reject if Google returned an error (e.g. user denied consent).
    2. Validate the CSRF state parameter (single-use, 10-minute TTL).
    3. Exchange the authorization code for Google tokens (backend-to-backend).
    4. Verify the ID token signature using Google's cached JWKS.
    5. Resolve or provision a local user (account linking / creation).
    6. Issue our own JWT access + refresh pair and set the HttpOnly cookie.
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    # Google may return an error (e.g. "access_denied") instead of a code
    if error:
        _audit_logger.log(
            AuditEventType.GOOGLE_LOGIN_FAILURE,
            ip_address=ip,
            user_agent=ua,
            detail=f"Google returned error: {error}",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter.",
        )

    # CSRF protection
    google.consume_state(state)

    try:
        # Backend code exchange
        token_response = await google.exchange_code(code)

        id_token_str: str | None = token_response.get("id_token")
        if not id_token_str:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google token response did not include an ID token.",
            )

        # OIDC verification
        claims = await google.verify_id_token(id_token_str)

        # Account linking / provisioning
        user = await google.get_or_create_user(claims)

    except HTTPException:
        _audit_logger.log(
            AuditEventType.GOOGLE_LOGIN_FAILURE,
            ip_address=ip,
            user_agent=ua,
            detail="OAuth flow error.",
        )
        raise

    # Mint our own JWT pair — same lifecycle as native login
    result = auth.issue_tokens(user)

    _audit_logger.log(
        AuditEventType.GOOGLE_LOGIN_SUCCESS,
        email=user.email,
        user_id=str(user.id),
        ip_address=ip,
        user_agent=ua,
    )

    _set_refresh_cookie(response, result.refresh_token)
    return result
