"""ReadinessChecker — concurrent dependency health verification."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DependencyStatus:
    name: str
    status: str  # "up" | "down"
    latency_ms: float | None = None
    error: str | None = None


@dataclass
class ReadinessResult:
    status: str  # "ok" | "degraded"
    dependencies: list[DependencyStatus] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dependencies": [
                {
                    "name": d.name,
                    "status": d.status,
                    "latency_ms": d.latency_ms,
                    "error": d.error,
                }
                for d in self.dependencies
            ],
        }


class ReadinessChecker:
    """Register async dependency checks and run them concurrently."""

    def __init__(self) -> None:
        self._checks: list[tuple[str, Callable[[], Coroutine[Any, Any, DependencyStatus]]]] = []

    def add(
        self,
        name: str,
        coro_fn: Callable[[], Coroutine[Any, Any, DependencyStatus]],
    ) -> None:
        self._checks.append((name, coro_fn))

    async def check(self) -> ReadinessResult:
        results = await asyncio.gather(
            *[fn() for _, fn in self._checks],
            return_exceptions=True,
        )
        statuses: list[DependencyStatus] = []
        for (name, _), result in zip(self._checks, results):
            if isinstance(result, Exception):
                statuses.append(DependencyStatus(name=name, status="down", error=str(result)))
            else:
                statuses.append(result)
        overall = "ok" if all(s.status == "up" for s in statuses) else "degraded"
        return ReadinessResult(status=overall, dependencies=statuses)
