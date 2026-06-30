"""Alembic migration environment — async engine with all models registered."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Register all ORM models so Alembic can see them
import app.models.access_decision_log  # noqa: F401
import app.models.isolation_policy  # noqa: F401
import app.models.lifecycle_event  # noqa: F401
import app.models.lifecycle_state  # noqa: F401
import app.models.resource_claim  # noqa: F401
import app.models.tenant  # noqa: F401
import app.models.tenant_contact  # noqa: F401
import app.models.tenant_metadata  # noqa: F401
import app.models.tenant_settings  # noqa: F401
from app.core.config import settings
from app.infrastructure.database.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
