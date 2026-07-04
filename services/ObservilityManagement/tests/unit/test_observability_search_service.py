from __future__ import annotations

from app.domains.logging.repositories.log_repository import LogEntry
from app.domains.observability.services.search_service import SearchService
from app.domains.tracing.repositories.trace_repository import TraceSummary


class _FakeLog:
    def __init__(self, entries: list[LogEntry] | None) -> None:
        self._entries = entries

    async def search(self, *, text: str, minutes: float = 15.0, limit: int = 50) -> list[LogEntry]:
        if self._entries is None:
            raise RuntimeError("Loki down")
        return self._entries


class _FakeTrace:
    def __init__(self, summaries: list[TraceSummary] | None) -> None:
        self._summaries = summaries

    async def search(
        self, *, query: str, minutes: float = 15.0, limit: int = 50
    ) -> list[TraceSummary]:
        if self._summaries is None:
            raise RuntimeError("Tempo down")
        return self._summaries


async def test_search_merges_logs_and_traces() -> None:
    logs = [LogEntry(timestamp="2024-01-01T00:00:02Z", line="boom")]
    traces = [
        TraceSummary(
            trace_id="t1",
            root_service="tenent",
            root_name="x",
            start_time="2024-01-01T00:00:01Z",
            duration_ms=1,
        )
    ]
    service = SearchService(_FakeLog(logs), _FakeTrace(traces))  # type: ignore[arg-type]
    results = await service.search(query="boom")
    assert [r.source for r in results] == ["log", "trace"]


async def test_search_degrades_when_logging_raises() -> None:
    traces = [
        TraceSummary(
            trace_id="t1",
            root_service="tenent",
            root_name="x",
            start_time="2024-01-01T00:00:01Z",
            duration_ms=1,
        )
    ]
    service = SearchService(_FakeLog(None), _FakeTrace(traces))  # type: ignore[arg-type]
    results = await service.search(query="boom")
    assert len(results) == 1
    assert results[0].source == "trace"


async def test_search_both_sources_failing_returns_empty_list() -> None:
    service = SearchService(_FakeLog(None), _FakeTrace(None))  # type: ignore[arg-type]
    assert await service.search(query="anything") == []
