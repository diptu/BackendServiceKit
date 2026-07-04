from __future__ import annotations

from app.domains.logging.repositories.log_repository import (
    build_logql_query,
    parse_query_range_response,
)


def test_build_logql_query_no_filters() -> None:
    assert build_logql_query() == '{job=~".+"}'


def test_build_logql_query_with_service_and_level() -> None:
    query = build_logql_query(service="tenent", level="error")
    assert 'service="tenent"' in query
    assert 'level="error"' in query


def test_build_logql_query_with_text_filter() -> None:
    query = build_logql_query(text="boom")
    assert "|= `boom`" in query


def test_build_logql_query_escapes_backticks() -> None:
    query = build_logql_query(text="weird`text")
    assert "`" not in query.split("|=")[1].strip().strip("`")


def test_parse_query_range_response_empty() -> None:
    assert parse_query_range_response({}) == []


def test_parse_query_range_response_real_shape() -> None:
    raw = {
        "data": {
            "result": [
                {
                    "stream": {"service": "tenent", "level": "error"},
                    "values": [
                        ["1700000000000000000", "boom happened"],
                        ["1700000001000000000", "boom happened again"],
                    ],
                }
            ]
        }
    }
    entries = parse_query_range_response(raw)
    assert len(entries) == 2
    assert entries[0].line in ("boom happened", "boom happened again")
    assert entries[0].labels == {"service": "tenent", "level": "error"}
    # sorted newest-first
    assert entries[0].timestamp >= entries[1].timestamp


def test_parse_query_range_response_malformed_values_ignored_safely() -> None:
    raw = {"data": {"result": [{"stream": {}, "values": ["not-a-pair", None, [1, 2, 3]]}]}}
    assert parse_query_range_response(raw) == []
