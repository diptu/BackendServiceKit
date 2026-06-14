from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.rbac import DEFAULT_ROLE
from app.core.security import create_access_token, hash_password, verify_password
from app.models.role import Role
from app.models.user import ACTIVE_REFRESH_TOKENS, User
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.user import TokenMatrixResponse, UserCreate, UserOut


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
    ):
        self.user_repository = user_repository
        self.role_repository = role_repository

    async def register(
        self,
        payload: UserCreate,
    ) -> User:
        email = payload.email.strip().lower()

        existing_user = await self.user_repository.get_by_email(email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )

        default_role = await self.role_repository.get_by_slug(DEFAULT_ROLE.value)

        # If the database was never seeded, create the GUEST role on the fly
        if not default_role:
            default_role = Role(
                slug=DEFAULT_ROLE.value,
                name=DEFAULT_ROLE.value.replace("_", " ").title(),
                is_system=True,
            )

        if not default_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default role not found.",
            )

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            is_active=True,
            is_verified=False,
            is_superuser=False,
            roles=[default_role],
        )

        return await self.user_repository.create(user)

    async def login(
        self,
        email: str,
        password: str,
    ) -> TokenMatrixResponse:
        email = email.strip().lower()

        user = await self.user_repository.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account disabled.",
            )

        roles = [role.name for role in user.roles]

        permissions: list[str] = []

        for role in user.roles:
            permissions.extend(p.name for p in role.permissions)

        permissions = list(set(permissions))

        now = datetime.now(UTC)

        access_jti = str(uuid4())
        refresh_jti = str(uuid4())

        access_claims: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
            "jti": access_jti,
            "roles": roles,
            "permissions": permissions,
            "type": "access",
        }

        refresh_claims: dict[str, Any] = {
            "sub": str(user.id),
            "jti": refresh_jti,
            "roles": roles,
            "permissions": permissions,
            "type": "refresh",
        }

        access_token = create_access_token(
            data=access_claims,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        refresh_token = create_access_token(
            data=refresh_claims,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        user.last_login_at = now

        await self.user_repository.update_last_login(user)

        ACTIVE_REFRESH_TOKENS[refresh_jti] = {
            "user_id": str(user.id),
            "revoked": False,
            "expires_at": (now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)),
        }

        return TokenMatrixResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            user=UserOut.model_validate(user),
        )
