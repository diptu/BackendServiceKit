from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import settings

# OAuth2 scheme — tokenUrl powers the Swagger UI "Authorize" modal form
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


async def is_authenticated(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, Any]:
    """
    FastAPI dependency: extracts the Bearer token via OAuth2PasswordBearer,
    decodes and validates JWT claims, and returns the payload dict.
    Using Depends(oauth2_scheme) causes FastAPI to emit the securityScheme
    into the OpenAPI spec and attach the lock icon to protected routes.

    If JWTContextMiddleware already decoded this exact access token at the
    edge, reuse its result instead of decoding twice — pure optimization,
    identical external behavior (same exceptions, same return shape) when
    the middleware isn't present, e.g. in unit tests that call this
    function directly or hit the app without going through the ASGI stack.
    """
    cached_claims: dict[str, Any] | None = getattr(request.state, "jwt_claims", None)
    if cached_claims is not None:
        return cached_claims

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token has expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if sub is None or token_type != "access":  # noqa: S105
            raise credentials_exception

        return payload

    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError) as exc:
        raise credentials_exception from exc


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(10)
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Generate an OAuth2/JWT access token containing identity metadata.
    """
    to_encode = data.copy()

    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
