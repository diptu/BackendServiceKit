from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_async_db, get_current_user
from app.audit.logger import AuditLogger
from app.core.config import settings
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.user import (
    LogoutRequest,
    RefreshTokenRequest,
    TokenMatrixResponse,
    UserCreate,
    UserOut,
)
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

_audit_logger = AuditLogger()

_REFRESH_COOKIE = "refresh_token"
_COOKIE_PATH = "/api/v1/auth"


def get_auth_service(
    db: AsyncSession = Depends(get_async_db),
) -> AuthService:
    return AuthService(
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
        audit_logger=_audit_logger,
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400,
        path=_COOKIE_PATH,
    )


def _extract_refresh_token(
    request: Request,
    body_token: str | None,
) -> str:
    token = request.cookies.get(_REFRESH_COOKIE) or body_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing.",
        )
    return token


# ---------------------------------------------------------------------------
# Current user (protected — shows the lock icon in Swagger UI)
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    return current_user


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserCreate,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return await service.register(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenMatrixResponse,
)
async def login(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    result = await service.login(
        email=form_data.username,
        password=form_data.password,
        ip_address=ip,
        user_agent=ua,
    )

    _set_refresh_cookie(response, result.refresh_token)
    return result


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


@router.post(
    "/refresh",
    response_model=TokenMatrixResponse,
)
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    body: Annotated[RefreshTokenRequest | None, Body()] = None,
):
    token = _extract_refresh_token(request, body.refresh_token if body else None)
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    result = await service.refresh(token, ip_address=ip, user_agent=ua)

    _set_refresh_cookie(response, result.refresh_token)
    return result


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    body: Annotated[LogoutRequest | None, Body()] = None,
):
    token = _extract_refresh_token(request, body.refresh_token if body else None)
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    await service.logout(token, ip_address=ip, user_agent=ua)

    response.delete_cookie(key=_REFRESH_COOKIE, path=_COOKIE_PATH)
