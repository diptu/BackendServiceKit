"""Normalizes each target's genuinely different `/ready` shape into a
common `list[DependencyStatus]`.

Dispatch is on the *shape* of the JSON (is "dependencies" present, is it a
list or dict), never on the calling target's name — a new target with one
of these shapes needs no change here.
"""

from __future__ import annotations

from typing import Any

from app.domains.health.models import DependencyStatus

_UP_STRINGS = {"ok", "ready", "up", "true", "healthy"}
_DOWN_STRINGS = {"unavailable", "down", "degraded", "false", "unhealthy"}


def normalize_ready_body(raw: dict[str, Any] | None) -> list[DependencyStatus]:
    if not raw:
        return []

    dependencies = raw.get("dependencies")

    if isinstance(dependencies, list):
        return _parse_list_shape(dependencies)

    if isinstance(dependencies, dict):
        return _parse_dict_shape(dependencies)

    return _parse_flat_shape(raw)


def _parse_list_shape(items: list[Any]) -> list[DependencyStatus]:
    result = []
    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            continue
        result.append(
            DependencyStatus(
                name=str(item["name"]),
                status=_normalize_status_value(item.get("status")),
                latency_ms=item.get("latency_ms"),
                error=item.get("error"),
            )
        )
    return result


def _parse_dict_shape(items: dict[str, Any]) -> list[DependencyStatus]:
    return [
        DependencyStatus(name=str(name), status=_normalize_status_value(value))
        for name, value in items.items()
    ]


def _parse_flat_shape(raw: dict[str, Any]) -> list[DependencyStatus]:
    result = []
    for key, value in raw.items():
        if key == "status":
            continue
        if isinstance(value, bool):
            result.append(DependencyStatus(name=key, status="up" if value else "down"))
        elif isinstance(value, str) and (
            value.lower() in _UP_STRINGS or value.lower() in _DOWN_STRINGS
        ):
            result.append(DependencyStatus(name=key, status=_normalize_status_value(value)))
    return result


def _normalize_status_value(value: Any) -> str:
    if isinstance(value, bool):
        return "up" if value else "down"
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in _UP_STRINGS:
            return "up"
        if lowered in _DOWN_STRINGS:
            return "down"
    return "unknown"
