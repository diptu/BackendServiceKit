from __future__ import annotations

from app.domain.span import Span, Trace


def _span(span_id: str, parent: str | None, start: int, end: int) -> Span:
    return Span(
        span_id=span_id,
        parent_span_id=parent,
        name=f"op-{span_id}",
        service="tenent",
        start_ns=start,
        end_ns=end,
        status="ok",
    )


def test_root_span_is_the_one_with_no_parent() -> None:
    trace = Trace(
        trace_id="t1",
        spans=[
            _span("child", "root", 10, 20),
            _span("root", None, 0, 100),
        ],
    )
    root = trace.root_span
    assert root is not None
    assert root.span_id == "root"


def test_root_span_falls_back_to_first_when_parent_is_dangling() -> None:
    # parent_span_id points at a span not present in this trace
    trace = Trace(trace_id="t1", spans=[_span("orphan", "missing-parent", 0, 50)])
    root = trace.root_span
    assert root is not None
    assert root.span_id == "orphan"


def test_root_span_none_for_empty_trace() -> None:
    trace = Trace(trace_id="t1", spans=[])
    assert trace.root_span is None


def test_trace_duration_spans_min_start_to_max_end() -> None:
    trace = Trace(
        trace_id="t1",
        spans=[_span("a", None, 100, 200), _span("b", "a", 150, 400)],
    )
    assert trace.start_ns == 100
    assert trace.end_ns == 400
    assert trace.duration_ns == 300


def test_trace_service_names_deduplicates() -> None:
    trace = Trace(
        trace_id="t1",
        spans=[_span("a", None, 0, 10), _span("b", "a", 0, 10)],
    )
    assert trace.service_names == {"tenent"}


def test_span_duration_never_negative() -> None:
    span = _span("a", None, 100, 50)
    assert span.duration_ns == 0
