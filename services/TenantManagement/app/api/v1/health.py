"""Backward-compatibility shim — canonical definition moved to health_router.py."""

from app.api.v1.health_router import health, ready, router

__all__ = ["health", "ready", "router"]
