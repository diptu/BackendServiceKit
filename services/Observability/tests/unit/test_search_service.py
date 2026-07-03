from __future__ import annotations

from typing import Any

from app.services.search_service import SearchService


class _FakeLoggingClient:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def search(
        self, *, query: str, minutes: float = 15.0, limit: int = 50
    ) -> dict[str, Any] | None:
        return self._body


class _FakeTracingClient:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def search(
        self, *, query: str, minutes: float = 15.0, limit: int = 50
    ) -> dict[str, Any] | None:
        return self._body


async def test_search_merges_logs_and_traces() -> None:
    logging_body = {"items": [{"timestamp": "2024-01-01T00:00:02Z", "message": "boom"}]}
    tracing_body = {"items": [{"timestamp": "2024-01-01T00:00:01Z", "trace_id": "t1"}]}
    service = SearchService(_FakeLoggingClient(logging_body), _FakeTracingClient(tracing_body))  # type: ignore[arg-type]

    results = await service.search(query="boom")
    assert [r.source for r in results] == ["log", "trace"]  # sorted newest-first


async def test_search_degrades_when_one_source_unreachable() -> None:
    tracing_body = {"items": [{"timestamp": "2024-01-01T00:00:01Z", "trace_id": "t1"}]}
    service = SearchService(_FakeLoggingClient(None), _FakeTracingClient(tracing_body))  # type: ignore[arg-type]

    results = await service.search(query="boom")
    assert len(results) == 1
    assert results[0].source == "trace"


async def test_search_respects_limit() -> None:
    logging_body = {
        "items": [
            {"timestamp": f"2024-01-01T00:00:{i:02d}Z", "message": f"m{i}"} for i in range(10)
        ]
    }
    service = SearchService(_FakeLoggingClient(logging_body), _FakeTracingClient(None))  # type: ignore[arg-type]

    results = await service.search(query="m", limit=3)
    assert len(results) == 3


async def test_search_both_sources_empty_returns_empty_list() -> None:
    service = SearchService(_FakeLoggingClient(None), _FakeTracingClient(None))  # type: ignore[arg-type]
    results = await service.search(query="anything")
    assert results == []
