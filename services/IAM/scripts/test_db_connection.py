"""Simple database connectivity test.

Usage:
    python scripts/test_db_connection.py

Purpose:
    - Verify database credentials.
    - Confirm network connectivity.
    - Validate SQLAlchemy configuration.
    - Useful for CI/CD health checks.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def test_database_connection() -> None:
    """Verify connectivity to PostgreSQL."""

    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version();"))
            postgres_version = result.scalar()

            print("✅ Database connection successful")
            print(f"PostgreSQL Version: {postgres_version}")

    except Exception as exc:
        print("❌ Database connection failed")
        print(f"Error: {exc}")
        raise

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_database_connection())