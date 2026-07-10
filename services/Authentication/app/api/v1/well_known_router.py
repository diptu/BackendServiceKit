"""Well-known discovery endpoints.

`/.well-known/jwks.json` publishes this service's public signing key(s) so
every other service (APIGateway, Tenent, …) can verify access tokens locally
without ever holding a private key. Under HS256 the key set is empty by
design — a shared secret is never published — which is itself the signal that
this deployment has not yet moved to asymmetric signing.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.token_service import get_jwks

router = APIRouter(tags=["Discovery"])


@router.get("/.well-known/jwks.json")
async def jwks() -> dict[str, list[dict[str, Any]]]:
    return get_jwks()
