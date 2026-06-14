from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_async_db
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.user import TokenMatrixResponse, UserCreate, UserOut
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def get_auth_service(
    db: AsyncSession = Depends(get_async_db),
) -> AuthService:
    return AuthService(
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
    )


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
        # Catch internal domain logic errors and map them to HTTP responses
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.post(
    "/login",
    response_model=TokenMatrixResponse,
)
async def login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    service: AuthService = Depends(get_auth_service),
):
    return await service.login(
        email=form_data.username,
        password=form_data.password,
    )
