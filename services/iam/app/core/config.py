from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(f"Loading environment variables from: {BASE_DIR}")
ENV_FILE = BASE_DIR / ".env"

# 2. Seed system environment with local configuration files prior to instantiation
load_dotenv(dotenv_path=ENV_FILE, override=False)


class Settings(BaseSettings):
    # Service Identifiers
    SERVICE_NAME: str = "IAM Service"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8000

    # Architecture Context
    DATABASE_URL: str | None = None
    UPLOAD_DIR: str = "media/iam"
    DEFAULT_USER_IMAGE: str = Field(
        default="microblog-platform/apps/iam-service/iam_service/assets/user.png"
    )

    # Stateful Cryptography Matrices
    SECRET_KEY: str = Field(default="InsecureDevelopmentFallbackKeyDoNotUseInProd")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cookie security — set False only in local HTTP dev environments
    COOKIE_SECURE: bool = True

    # Password reset
    FRONTEND_URL: str = "http://localhost:3000"
    RESET_TOKEN_TTL_MINUTES: int = 15

    # Logging
    LOG_LEVEL: str = "INFO"

    # Google OAuth2 / OIDC — all values must be set via environment / .env in production.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"  # noqa: S105
    GOOGLE_JWKS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"

    model_config = SettingsConfigDict(extra="ignore", env_file=None)


settings = Settings()
