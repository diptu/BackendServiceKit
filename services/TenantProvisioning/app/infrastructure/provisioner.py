"""Physical database provisioners.

The seam between "a tenant needs a database" and "a database exists." The
`LocalDatabaseProvisioner` creates a per-tenant SQLite file (usable in dev/test
with no server), and `PostgresDatabaseProvisioner` runs `CREATE DATABASE`
against an admin connection. `SsoService`-style injection means the workflow is
tested against real SQLite files without mocking.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


class ProvisionedDatabase:
    __slots__ = ("driver", "host", "port", "name", "user", "secret_ref", "dsn")

    def __init__(
        self,
        *,
        driver: str,
        host: str,
        port: int,
        name: str,
        user: str,
        secret_ref: str | None,
        dsn: str,
    ) -> None:
        self.driver = driver
        self.host = host
        self.port = port
        self.name = name
        self.user = user
        self.secret_ref = secret_ref
        self.dsn = dsn


class DatabaseProvisioner(ABC):
    @abstractmethod
    async def create(self, tenant_id: uuid.UUID) -> ProvisionedDatabase: ...

    @abstractmethod
    async def drop(self, tenant_id: uuid.UUID) -> None: ...


class LocalDatabaseProvisioner(DatabaseProvisioner):
    """Dev/test backend — one SQLite file per tenant. No CREATE DATABASE."""

    def __init__(self, directory: str) -> None:
        self._dir = directory

    def _path(self, tenant_id: uuid.UUID) -> str:
        return os.path.join(self._dir, f"tenant_{tenant_id.hex}.db")

    async def create(self, tenant_id: uuid.UUID) -> ProvisionedDatabase:
        os.makedirs(self._dir, exist_ok=True)
        dsn = f"sqlite+aiosqlite:///{self._path(tenant_id)}"
        # Touch the database so it materializes.
        engine = create_async_engine(dsn, connect_args={"check_same_thread": False})
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        finally:
            await engine.dispose()
        return ProvisionedDatabase(
            driver="sqlite+aiosqlite",
            host="local",
            port=0,
            name=f"tenant_{tenant_id.hex}.db",
            user="",
            secret_ref=None,
            dsn=dsn,
        )

    async def drop(self, tenant_id: uuid.UUID) -> None:
        path = self._path(tenant_id)
        if os.path.exists(path):
            os.remove(path)


class PostgresDatabaseProvisioner(DatabaseProvisioner):
    """Runs CREATE/DROP DATABASE against an admin connection, then hands back
    the tenant's own DSN derived from the configured template."""

    def __init__(self, admin_url: str, url_template: str) -> None:
        self._admin_url = admin_url
        self._template = url_template

    @staticmethod
    def _db_name(tenant_id: uuid.UUID) -> str:
        return f"tenant_{tenant_id.hex}"

    async def create(self, tenant_id: uuid.UUID) -> ProvisionedDatabase:
        db_name = self._db_name(tenant_id)
        # CREATE DATABASE cannot run inside a transaction — use AUTOCOMMIT.
        engine = create_async_engine(self._admin_url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                exists = await conn.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname = :n"),
                    {"n": db_name},
                )
                if not exists:
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        finally:
            await engine.dispose()
        dsn = self._template.replace("{tenant}", tenant_id.hex)
        return ProvisionedDatabase(
            driver="postgresql+asyncpg",
            host=_host_of(dsn),
            port=5432,
            name=db_name,
            user=_user_of(dsn),
            secret_ref=f"tenant/{tenant_id.hex}/db",
            dsn=dsn,
        )

    async def drop(self, tenant_id: uuid.UUID) -> None:
        db_name = self._db_name(tenant_id)
        engine = create_async_engine(self._admin_url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            await engine.dispose()


def _host_of(dsn: str) -> str:
    # postgresql+asyncpg://user:pw@host:port/name → host
    try:
        return dsn.split("@", 1)[1].split(":", 1)[0].split("/", 1)[0]
    except IndexError:
        return "localhost"


def _user_of(dsn: str) -> str:
    try:
        return dsn.split("://", 1)[1].split(":", 1)[0]
    except IndexError:
        return "postgres"


def build_provisioner() -> DatabaseProvisioner:
    if settings.provisioner_backend == "postgres":
        if not settings.admin_database_url:
            raise RuntimeError(
                "provisioner_backend=postgres requires admin_database_url."
            )
        return PostgresDatabaseProvisioner(
            settings.admin_database_url, settings.tenant_database_url_template
        )
    return LocalDatabaseProvisioner(settings.local_provisioner_dir)
