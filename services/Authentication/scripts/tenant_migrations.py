"""Per-tenant migration orchestrator for Siloed multi-tenancy.

Never run tenant migrations by hand. This is the "flight control" script the
TODO calls for: it resolves each tenant to its own database and applies
`alembic upgrade head` to it, one at a time, reporting per-tenant success or
failure. It is **resumable and idempotent** — re-running after a partial
failure simply re-applies head (a no-op) to the tenants already at head and
retries the ones that failed.

The tenant list is the Control Plane's job to own; until Tenent exposes it,
pass tenant ids explicitly (argv) or as a comma-separated `AUTH_TENANT_IDS`
env var.

Usage:
    uv run python -m scripts.tenant_migrations upgrade <tenant_id> [<tenant_id> ...]
    AUTH_TENANT_IDS="<uuid>,<uuid>" uv run python -m scripts.tenant_migrations upgrade
    uv run python -m scripts.tenant_migrations provision <tenant_id>   # create + migrate
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# Put the service dir (for `app`) and the repo root (for `shared`) on the path
# so this runs as a standalone script, not just under pytest's pythonpath.
_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(_SERVICE_ROOT), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.core.config import settings  # noqa: E402
from shared.db.resolver import TemplateConnectionResolver  # noqa: E402

_ALEMBIC_INI = _SERVICE_ROOT / "alembic.ini"


def _resolver() -> TemplateConnectionResolver:
    return TemplateConnectionResolver(
        template=settings.tenant_database_url_template or "",
        overrides=settings.tenant_database_overrides,
    )


def _tenant_ids(args: list[str]) -> list[UUID]:
    raw = args or [
        t for t in os.environ.get("AUTH_TENANT_IDS", "").split(",") if t.strip()
    ]
    if not raw:
        raise SystemExit(
            "No tenant ids given (pass as args or set AUTH_TENANT_IDS=uuid,uuid)."
        )
    return [UUID(t.strip()) for t in raw]


def _upgrade_one(db_url: str) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    # env.py reads ALEMBIC_TARGET_URL to pick the database to migrate.
    os.environ["ALEMBIC_TARGET_URL"] = db_url
    try:
        command.upgrade(cfg, "head")
    finally:
        os.environ.pop("ALEMBIC_TARGET_URL", None)


def _run(tenant_ids: list[UUID]) -> int:
    # Synchronous on purpose: Alembic's env.py runs its own asyncio loop per
    # upgrade, so this loop must NOT itself be inside asyncio.run (that nests
    # event loops). Each tenant's URL resolution gets a short-lived loop.
    resolver = _resolver()
    failures = 0
    for tenant_id in tenant_ids:
        try:
            db_url = asyncio.run(resolver.resolve(tenant_id))
            _upgrade_one(db_url)
            print(f"[ok]   {tenant_id} -> head")
        except Exception as exc:  # noqa: BLE001 — report and continue per tenant
            failures += 1
            print(f"[FAIL] {tenant_id}: {exc}", file=sys.stderr)
    total = len(tenant_ids)
    print(f"\n{total - failures}/{total} tenant databases at head.")
    return failures


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"upgrade", "provision"}:
        raise SystemExit("Usage: tenant_migrations <upgrade|provision> [tenant_id ...]")
    if not settings.siloed_multitenancy_enabled:
        print(
            "WARNING: siloed_multitenancy_enabled is off — this only makes "
            "sense with per-tenant databases configured.",
            file=sys.stderr,
        )
    tenant_ids = _tenant_ids(argv[1:])
    # `provision` and `upgrade` are the same DDL operation here (upgrade head
    # into the tenant DB); physical database creation is deployment-specific
    # (CREATE DATABASE / managed provisioning) and belongs to Tenent.
    return _run(tenant_ids)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
