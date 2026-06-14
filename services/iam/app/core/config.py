from pathlib import Path

from dotenv import load_dotenv
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
    DEFAULT_USER_IMAGE: str = (
        "microblog-platform/apps/iam-service/iam_service/assets/user.png"
    )

    # Stateful Cryptography Matrices
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(extra="ignore", env_file=None)


settings = Settings()
