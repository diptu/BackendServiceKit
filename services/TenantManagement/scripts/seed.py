#!/usr/bin/env python3
"""Seed script for the Tenant Management Service.

Generates deterministic, production-like demo data for local development,
automated testing, demonstrations, and CI/CD pipelines.

Seeded entities (scoped to what this service owns):
  - Tenants         — Alphabet Corporation, Meta Platforms
  - TenantSettings  — per-tenant configuration defaults
  - TenantMetadata  — key-value enrichment (industry, tier, org list, …)
  - TenantContacts  — owners and admins (user_id projections, no real users)

Usage
-----
    uv run python scripts/seed.py                   # deterministic (--seed 42)
    uv run python scripts/seed.py --seed 99         # custom seed value
    uv run python scripts/seed.py --random          # non-deterministic UUIDs
    uv run python scripts/seed.py --reset           # drop seed rows, then re-seed
    uv run python scripts/seed.py --dry-run         # print plan; no DB connection

Safety
------
    The script refuses to run (exits 1) if DATABASE_URL contains the word "prod"
    unless --dry-run is also passed.
    It must never be wired into automatic production pipelines.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make 'app' importable regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# ANSI helpers (no external dependencies)
# ---------------------------------------------------------------------------

_TTY = sys.stdout.isatty()


class _C:
    RESET = "\033[0m" if _TTY else ""
    BOLD = "\033[1m" if _TTY else ""
    DIM = "\033[2m" if _TTY else ""
    GREEN = "\033[32m" if _TTY else ""
    YELLOW = "\033[33m" if _TTY else ""
    BLUE = "\033[34m" if _TTY else ""
    CYAN = "\033[36m" if _TTY else ""
    RED = "\033[31m" if _TTY else ""


def _ok(msg: str) -> None:
    print(f"  {_C.GREEN}✓{_C.RESET}  {msg}")


def _skip(msg: str) -> None:
    print(f"  {_C.YELLOW}~{_C.RESET}  {msg} {_C.DIM}(already exists){_C.RESET}")


def _plan(msg: str) -> None:
    print(f"  {_C.CYAN}»{_C.RESET}  {msg}")


def _section(title: str) -> None:
    print(f"\n{_C.BOLD}{_C.BLUE}▸ {title}{_C.RESET}")


def _die(msg: str) -> None:
    print(f"\n{_C.RED}{_C.BOLD}ERROR:{_C.RESET} {msg}\n", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Deterministic UUID generation
# ---------------------------------------------------------------------------


def _uuid(rng: random.Random) -> uuid.UUID:
    """Return a UUID v4 whose randomness comes from *rng*."""
    return uuid.UUID(int=rng.getrandbits(128), version=4)


# ---------------------------------------------------------------------------
# Seed data catalog
# ---------------------------------------------------------------------------
# Based on the SeedDataService README examples.  The TenantManagement service
# only stores tenants and their direct sub-resources; organisation, user, role,
# and group records belong to other services and are not seeded here.

_CATALOG: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ Alphabet
    {
        "slug": "alphabet-corp",
        "display_name": "Alphabet Corporation",
        "description": (
            "Google's parent company and one of the world's largest technology "
            "conglomerates, operating Google Search, YouTube, and DeepMind."
        ),
        "region": "us-east-1",
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "currency": "USD",
        "settings": {
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "language": "en",
            "date_format": "YYYY-MM-DD",
            "number_format": "#,###.##",
            "currency": "USD",
            "session_timeout_minutes": 60,
            "default_theme": "light",
        },
        "metadata": {
            "industry": "Technology",
            "company_size": "enterprise",
            "customer_tier": "platinum",
            "support_plan": "premium",
            # Downstream services use this hint to bootstrap org-level seed data
            "organizations": "Google Search,YouTube,DeepMind",
            "headquarters": "Mountain View, CA",
            "founded": "2015",
            "employee_count": "190000",
        },
        "contacts": [
            {"role": "owner"},
            {"role": "owner"},
            {"role": "admin"},
            {"role": "admin"},
        ],
    },
    # ------------------------------------------------------------------ Meta
    {
        "slug": "meta-platforms",
        "display_name": "Meta Platforms",
        "description": (
            "Social media and technology company operating Facebook, Instagram, "
            "and WhatsApp, serving over 3 billion monthly active users."
        ),
        "region": "us-west-2",
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "currency": "USD",
        "settings": {
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "language": "en",
            "date_format": "MM/DD/YYYY",
            "number_format": "#,###.##",
            "currency": "USD",
            "session_timeout_minutes": 30,
            "default_theme": "dark",
        },
        "metadata": {
            "industry": "Technology",
            "company_size": "enterprise",
            "customer_tier": "gold",
            "support_plan": "premium",
            "organizations": "Facebook,Instagram,WhatsApp",
            "headquarters": "Menlo Park, CA",
            "founded": "2004",
            "employee_count": "86000",
        },
        "contacts": [
            {"role": "owner"},
            {"role": "admin"},
            {"role": "admin"},
        ],
    },
]

_CATALOG_SLUGS = [entry["slug"] for entry in _CATALOG]


# ---------------------------------------------------------------------------
# Dry-run plan printer (zero DB access)
# ---------------------------------------------------------------------------


def _print_dry_run(rng: random.Random) -> None:
    """Print what would be inserted without connecting to the database."""
    _section(f"Plan — {len(_CATALOG)} tenants")

    for entry in _CATALOG:
        slug = entry["slug"]
        contacts = entry["contacts"]
        owners = sum(1 for c in contacts if c["role"] == "owner")
        admins = sum(1 for c in contacts if c["role"] == "admin")

        print(f"\n  {_C.CYAN}{_C.BOLD}{entry['display_name']}{_C.RESET}")
        _plan(f"tenant    {_C.BOLD}{slug}{_C.RESET}  → id={_uuid(rng)}  region={entry['region']}")
        _plan(f"settings  {_C.BOLD}{slug}{_C.RESET}  → theme={entry['settings']['default_theme']}  timeout={entry['settings']['session_timeout_minutes']}m")
        _plan(f"metadata  {_C.BOLD}{slug}{_C.RESET}  → {len(entry['metadata'])} keys  ({', '.join(list(entry['metadata'])[:3])}, …)")
        _plan(f"contacts  {_C.BOLD}{slug}{_C.RESET}  → {owners} owners, {admins} admins")

    print(
        f"\n  {_C.YELLOW}Dry-run — no changes were written to the database.{_C.RESET}\n"
    )


# ---------------------------------------------------------------------------
# Live seeders
# ---------------------------------------------------------------------------


async def _seed_tenant(
    session: Any,
    entry: dict[str, Any],
    rng: random.Random,
) -> uuid.UUID:
    """Insert one tenant row.  Returns the UUID (existing or newly created)."""
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.domain.enums import TenantStatus

    row = await session.scalar(
        select(Tenant.id).where(Tenant.name == entry["slug"])
    )
    if row is not None:
        _skip(f"tenant    {_C.BOLD}{entry['slug']}{_C.RESET}")
        return row

    tenant_id = _uuid(rng)
    owner_id = _uuid(rng)
    now = datetime.now(timezone.utc)

    session.add(
        Tenant(
            id=tenant_id,
            name=entry["slug"],
            display_name=entry["display_name"],
            description=entry["description"],
            status=TenantStatus.DRAFT,
            region=entry["region"],
            timezone=entry["timezone"],
            locale=entry["locale"],
            currency=entry["currency"],
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    _ok(f"tenant    {_C.BOLD}{entry['slug']}{_C.RESET}  id={tenant_id}")
    return tenant_id


async def _seed_settings(
    session: Any,
    tenant_id: uuid.UUID,
    slug: str,
    cfg: dict[str, Any],
    rng: random.Random,
) -> None:
    """Insert TenantSettings — one row per tenant."""
    from sqlalchemy import func, select
    from app.models.tenant_settings import TenantSettings

    count = await session.scalar(
        select(func.count(TenantSettings.id)).where(
            TenantSettings.tenant_id == tenant_id
        )
    )
    if count:
        _skip(f"settings  {_C.BOLD}{slug}{_C.RESET}")
        return

    session.add(TenantSettings(id=_uuid(rng), tenant_id=tenant_id, **cfg))
    await session.flush()
    _ok(f"settings  {_C.BOLD}{slug}{_C.RESET}")


async def _seed_metadata(
    session: Any,
    tenant_id: uuid.UUID,
    slug: str,
    kv: dict[str, str],
    rng: random.Random,
) -> None:
    """Upsert metadata key-value pairs — idempotent per key."""
    from sqlalchemy import func, select
    from app.models.tenant_metadata import TenantMetadata

    now = datetime.now(timezone.utc)
    inserted = 0
    skipped = 0

    for key, value in kv.items():
        count = await session.scalar(
            select(func.count(TenantMetadata.id)).where(
                TenantMetadata.tenant_id == tenant_id,
                TenantMetadata.key == key,
            )
        )
        if count:
            skipped += 1
            continue

        session.add(
            TenantMetadata(
                id=_uuid(rng),
                tenant_id=tenant_id,
                key=key,
                value=value,
                created_at=now,
                updated_at=now,
            )
        )
        inserted += 1

    if inserted:
        await session.flush()
        _ok(
            f"metadata  {_C.BOLD}{slug}{_C.RESET}  "
            f"({inserted} inserted, {skipped} skipped)"
        )
    else:
        _skip(f"metadata  {_C.BOLD}{slug}{_C.RESET}  (all {skipped} keys)")


async def _seed_contacts(
    session: Any,
    tenant_id: uuid.UUID,
    slug: str,
    specs: list[dict[str, str]],
    rng: random.Random,
) -> None:
    """Insert TenantContacts if no active contacts exist yet."""
    from sqlalchemy import func, select
    from app.models.tenant_contact import TenantContact

    active = await session.scalar(
        select(func.count(TenantContact.id)).where(
            TenantContact.tenant_id == tenant_id,
            TenantContact.removed_at.is_(None),
        )
    )
    if active:
        _skip(
            f"contacts  {_C.BOLD}{slug}{_C.RESET}  "
            f"({active} active contacts already present)"
        )
        return

    now = datetime.now(timezone.utc)
    for spec in specs:
        session.add(
            TenantContact(
                id=_uuid(rng),
                tenant_id=tenant_id,
                user_id=_uuid(rng),
                role=spec["role"],
                added_at=now,
            )
        )
    await session.flush()

    owners = sum(1 for s in specs if s["role"] == "owner")
    admins = sum(1 for s in specs if s["role"] == "admin")
    _ok(f"contacts  {_C.BOLD}{slug}{_C.RESET}  ({owners} owners, {admins} admins)")


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


async def _reset_seed_data(session: Any) -> None:
    """Delete seed catalog rows (DB CASCADE removes sub-tables automatically)."""
    from sqlalchemy import delete, select
    from app.models.tenant import Tenant

    found = list(
        await session.scalars(
            select(Tenant.name).where(Tenant.name.in_(_CATALOG_SLUGS))
        )
    )
    if not found:
        print(f"  {_C.DIM}nothing to reset — no seed tenants found{_C.RESET}")
        return

    await session.execute(delete(Tenant).where(Tenant.name.in_(found)))
    await session.commit()

    for slug in found:
        _ok(f"deleted   {_C.BOLD}{slug}{_C.RESET}  (settings, metadata, contacts cascaded)")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="seed.py",
        description="Seed the Tenant Management Service with demo data.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--seed",
        type=int,
        default=42,
        metavar="INT",
        help="RNG seed for deterministic UUID generation (default: 42).",
    )
    mode.add_argument(
        "--random",
        dest="use_random",
        action="store_true",
        help="Generate non-deterministic UUIDs.",
    )
    p.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing seed data before inserting.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without connecting to the database.",
    )
    return p.parse_args()


async def _run(args: argparse.Namespace) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    # Deferred imports — avoids DB init on --help or --dry-run
    from app.core.config import settings
    from app.infrastructure.database.utils import resolve_ssl

    db_url = settings.database_url
    rng = random.Random() if args.use_random else random.Random(args.seed)
    mode_label = "random" if args.use_random else f"seed={args.seed}"

    print(f"\n{_C.BOLD}Tenant Management — seed.py{_C.RESET}")
    print(f"{_C.DIM}  database : {db_url}")
    print(f"  mode     : {mode_label}{_C.RESET}")

    # Production safety guard
    if "prod" in db_url.lower():
        _die(
            "DATABASE_URL appears to target a production database.\n"
            "  Point DATABASE_URL at a dev/test database and retry."
        )

    _url, _connect_args = resolve_ssl(db_url)
    engine = create_async_engine(_url, connect_args=_connect_args, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with SessionFactory() as session:

            if args.reset:
                _section("Reset")
                await _reset_seed_data(session)

            _section(f"Seeding {len(_CATALOG)} tenants")

            for entry in _CATALOG:
                slug = entry["slug"]
                print(f"\n  {_C.CYAN}{_C.BOLD}{entry['display_name']}{_C.RESET}")

                tenant_id = await _seed_tenant(session, entry, rng)
                await _seed_settings(session, tenant_id, slug, entry["settings"], rng)
                await _seed_metadata(session, tenant_id, slug, entry["metadata"], rng)
                await _seed_contacts(session, tenant_id, slug, entry["contacts"], rng)

            await session.commit()

        _section("Complete")
        print(f"  {_C.GREEN}Seed data committed successfully.{_C.RESET}\n")

    finally:
        await engine.dispose()


def main() -> None:
    args = _parse_args()

    rng = random.Random() if args.use_random else random.Random(args.seed)

    if args.dry_run:
        mode_label = "random" if args.use_random else f"seed={args.seed}"
        print(f"\n{_C.BOLD}Tenant Management — seed.py{_C.RESET}")
        print(f"{_C.DIM}  mode     : dry-run, {mode_label}{_C.RESET}")
        _print_dry_run(rng)
        return

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
