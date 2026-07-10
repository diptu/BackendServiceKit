"""Applies the managed services' schemas into a freshly-created tenant database.

Cross-service migration is genuinely out-of-process — each service owns its own
Alembic history. A production `SubprocessMigrationRunner` would shell out to
every managed service's `scripts/tenant_migrations.py` against the new DSN. The
default `MarkerMigrationRunner` connects to the tenant database and records
which services were migrated, giving the workflow a real, observable effect
without depending on every service's checkout being present.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


class MigrationRunner(ABC):
    @abstractmethod
    async def migrate(self, dsn: str, services: list[str]) -> None: ...


class MarkerMigrationRunner(MigrationRunner):
    async def migrate(self, dsn: str, services: list[str]) -> None:
        connect_args = {"check_same_thread": False} if dsn.startswith("sqlite") else {}
        engine = create_async_engine(dsn, connect_args=connect_args)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS provisioning_marker "
                        "(service VARCHAR(100) PRIMARY KEY)"
                    )
                )
                # Idempotent: clear then re-record, so a retry never collides.
                await conn.execute(text("DELETE FROM provisioning_marker"))
                for service in services:
                    await conn.execute(
                        text("INSERT INTO provisioning_marker (service) VALUES (:s)"),
                        {"s": service},
                    )
        finally:
            await engine.dispose()
