"""Database URL utilities."""

from __future__ import annotations

import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def resolve_ssl(url: str) -> tuple[str, dict[str, object]]:
    """Strip SSL query params from *url* and return an asyncpg-compatible pair."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_mode = (params.pop("sslmode", [None])[0] or "").lower()
    ssl_param = (params.pop("ssl", [None])[0] or "").lower()

    connect_args: dict[str, object] = {}

    if not ssl_mode and not ssl_param:
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
