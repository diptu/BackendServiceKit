"""Database URL utilities shared by engine, Alembic env, and scripts."""

from __future__ import annotations

import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def resolve_ssl(url: str) -> tuple[str, dict[str, object]]:
    """Strip SSL query params from *url* and return an asyncpg-compatible pair.

    asyncpg 0.29+ does not accept ``sslmode`` or ``ssl`` as URL query
    parameters — SSL must be passed as an ``ssl.SSLContext`` via
    ``connect_args``.  This function extracts those params, builds the context
    when SSL is requested, and returns a clean URL alongside the connect_args
    dict ready to pass to ``create_async_engine``.

    Args:
        url: Raw database URL, possibly containing ``?sslmode=require`` or
             ``?ssl=require`` (Neon.tech / cloud Postgres style).

    Returns:
        ``(clean_url, connect_args)`` — the URL with SSL params removed and a
        dict that is either empty (no SSL) or ``{"ssl": SSLContext}``.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_mode = (params.pop("sslmode", [None])[0] or "").lower()
    ssl_param = (params.pop("ssl", [None])[0] or "").lower()

    connect_args: dict[str, object] = {}

    if not ssl_mode and not ssl_param:
        # No SSL params present — return URL unchanged.
        # urlunparse mishandles non-standard schemes like sqlite+aiosqlite
        # (drops a slash from triple-slash paths), so we must not round-trip
        # the URL unless we actually have something to strip.
        return url, connect_args

    if ssl_mode in ("require", "verify-ca", "verify-full") or ssl_param in (
        "require",
        "true",
        "1",
    ):
        connect_args["ssl"] = ssl.create_default_context()

    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))
    return clean_url, connect_args
