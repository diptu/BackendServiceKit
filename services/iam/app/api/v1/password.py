from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_async_db, get_current_user
from app.audit.logger import AuditLogger
from app.repositories.password_reset import PasswordResetTokenRepository
from app.repositories.user import UserRepository
from app.schemas.password import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
)
from app.schemas.user import UserOut
from app.services.email import EmailService
from app.services.password import PasswordService

router = APIRouter(prefix="/auth/password", tags=["Password Management"])

_audit_logger = AuditLogger()
_email_service = EmailService()

_ENUMERATION_SAFE_MSG = (
    "If an account with that email exists, a password reset link has been sent."
)


def _get_password_service(
    db: AsyncSession = Depends(get_async_db),
) -> PasswordService:
    return PasswordService(
        user_repository=UserRepository(db),
        reset_token_repository=PasswordResetTokenRepository(db),
        email_service=_email_service,
        audit_logger=_audit_logger,
    )


# ---------------------------------------------------------------------------
# Change password (protected)
# ---------------------------------------------------------------------------


@router.post(
    "/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password for the authenticated user",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    service: PasswordService = Depends(_get_password_service),
) -> None:
    await service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


# ---------------------------------------------------------------------------
# Forgot password (open — always returns 202 regardless of email existence)
# ---------------------------------------------------------------------------


@router.post(
    "/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Request a password reset link",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    service: PasswordService = Depends(_get_password_service),
) -> MessageResponse:
    await service.forgot_password(
        email=str(payload.email),
        ip_address=request.client.host if request.client else None,
    )
    return MessageResponse(message=_ENUMERATION_SAFE_MSG)


# ---------------------------------------------------------------------------
# Reset password (open — consumes a single-use token)
# ---------------------------------------------------------------------------


@router.post(
    "/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset password using a valid single-use token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    service: PasswordService = Depends(_get_password_service),
) -> None:
    await service.reset_password(
        raw_token=payload.token,
        new_password=payload.new_password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
