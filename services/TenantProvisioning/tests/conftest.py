"""Session-level test configuration."""

import os

os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///./test_provisioning.sqlite"
)
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
# Disable rate limiting globally in tests so concurrent test suites don't
# accumulate counter state across fixtures within the same minute window.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
