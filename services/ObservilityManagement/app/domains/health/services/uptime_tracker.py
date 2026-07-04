"""In-memory, per-process tracker of *observed* uptime per target — this
domain's own observation of how long it has continuously seen a target
reachable, not a read of the target process's actual internal clock."""

from __future__ import annotations

import time


class UptimeTracker:
    def __init__(self) -> None:
        self._first_seen_reachable: dict[str, float] = {}

    def record(self, name: str, *, reachable: bool) -> float | None:
        now = time.monotonic()
        if not reachable:
            self._first_seen_reachable.pop(name, None)
            return None
        first_seen = self._first_seen_reachable.setdefault(name, now)
        return round(now - first_seen, 2)

    def clear(self) -> None:
        self._first_seen_reachable.clear()
