"""Liveness check — confirms the process is alive and responsive."""

from __future__ import annotations

import time
from datetime import datetime, timezone

_START_TIME = time.monotonic()


def liveness_handler() -> dict[str, object]:
    """Return a liveness payload suitable for /health/live endpoints."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.monotonic() - _START_TIME, 2),
    }
