"""Session-level test configuration."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_isolation.sqlite")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("JWT_AUTH_ENABLED", "false")
os.environ.setdefault("ENABLE_TRACING", "false")
