"""Alembic environment configuration with async SQLAlchemy support."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load DATABASE_URL via pydantic-settings (which reads .env automatically).
# This ensures the same URL resolution logic used by the app is also used
# for migrations — including SSL normalization.
from app.core.config import settings  # noqa: E402
from app.infrastructure.database.utils import resolve_ssl  # noqa: E402

_db_url, _connect_args = resolve_ssl(settings.database_url)
config.set_main_option("sqlalchemy.url", _db_url)

from app.infrastructure.database.base import Base  # noqa: E402
import app.models.tenant  # noqa: F401, E402
import app.models.tenant_settings  # noqa: F401, E402
import app.models.tenant_metadata  # noqa: F401, E402
import app.models.tenant_contact  # noqa: F401, E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: "Connection") -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        _db_url,
        connect_args=_connect_args,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
