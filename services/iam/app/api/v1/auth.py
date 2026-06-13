from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from app.api.v1.dependencies import \
    get_async_db  # Core session dependency injection
from app.core.config import settings
from app.core.security import (create_access_token, hash_password,
                               verify_password)
from app.models.role import \
    Role  # Explicit model instance for structural mapping
from app.models.user import ACTIVE_REFRESH_TOKENS  # Stateful tracking matrix
from app.models.user import User
from app.schemas.user import TokenMatrixResponse, UserCreate, UserOut
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/auth", tags=["IAM Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Registers a unique platform user, establishes base default roles, 
    and handles secure bcrypt hashing layers.
    """
    email_clean = payload.email.strip().lower()
    
    # Check global identity uniqueness constraints
    query = select(User).where(User.email == email_clean)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )
        
    # Query database engine for the standard operational default role
    role_query = select(Role).where(Role.name == "user")
    role_result = await db.execute(role_query)
    default_role = role_result.scalar_one_or_none()
    
    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Base platform RBAC 'user' role is unseeded in the database matrix."
        )

    # Securely translate plaintext into cryptographic signatures
    hashed_password = hash_password(payload.password)
    
    new_user = User(
        email=email_clean,
        password_hash=hashed_password,
        is_active=True,
        is_verified=False,
        is_superuser=False,
        roles=[default_role]
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=TokenMatrixResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Validates authentication credentials and generates a stateful access/refresh 
    token matrix alongside complete public user metadata profiles.
    """
    email_clean = form_data.username.strip().lower()
    
    # Retrieve user object mapping. Lazy Loading rule "selectin" on the model handles roles
    query = select(User).where(User.email == email_clean)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    # Evaluate credentials safely
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This user account has been deactivated."
        )

    # Consolidate permission scopes from current role instances
    assigned_roles = [role.name for role in user.roles]
    permissions = []
    for role in user.roles:
        if hasattr(role, "permissions"):
            permissions.extend([p.name for p in role.permissions])
            
    permissions = list(set(permissions))  # De-duplicate

    now = datetime.now(UTC)
    access_jti = str(uuid4())
    refresh_jti = str(uuid4())

    # Build Short-lived Access Token Claims Matrix
    access_token_data: dict[str, Any] = {
        "sub": str(user.id),
        "email": user.email,
        "jti": access_jti,
        "roles": assigned_roles,
        "permissions": permissions,
        "type": "access",
    }
    access_token = create_access_token(
        data=access_token_data, 
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Build Long-lived Stateful Refresh Token Claims Matrix
    refresh_token_data: dict[str, Any] = {
        "sub": str(user.id),
        "jti": refresh_jti,
        "roles": assigned_roles,
        "permissions": permissions,
        "type": "refresh",
    }
    refresh_token = create_access_token(
        data=refresh_token_data, 
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    # Trace metrics inside the data repository layer
    user.last_login_at = now
    await db.commit()
    await db.refresh(user)

    # Track state in the active verification index matrix
    ACTIVE_REFRESH_TOKENS[refresh_jti] = {
        "user_id": str(user.id),
        "revoked": False,
        "expires_at": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    }

    return TokenMatrixResponse(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )