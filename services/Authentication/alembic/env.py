import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Register all ORM models so Alembic can see them
import app.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.utils import resolve_ssl

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _target_url() -> str:
    """The database to migrate. Defaults to the shared-schema `database_url`,
    but the per-tenant migration orchestrator points this at each tenant DB in
    turn via `-x db_url=...` (or the `ALEMBIC_TARGET_URL` env var), so the same
    migrations apply across every tenant database. See TODO.md."""
    x_args = context.get_x_argument(as_dictionary=True)
    return (
        x_args.get("db_url")
        or os.environ.get("ALEMBIC_TARGET_URL")
        or settings.database_url
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_target_url(),
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
    url, connect_args = resolve_ssl(_target_url())
    engine = create_async_engine(
        url, connect_args=connect_args, poolclass=pool.NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
