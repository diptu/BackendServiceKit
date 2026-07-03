from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidLogQLError
from app.repositories.log_repository import build_logql, parse_streams


def test_build_logql_no_filters_uses_catchall_selector() -> None:
    assert build_logql() == '{service=~".+"}'


def test_build_logql_service_and_level_are_label_matchers() -> None:
    assert build_logql(service="tenent", level="error") == '{service="tenent", level="ERROR"}'


def test_build_logql_tenant_id_is_a_json_field_filter_not_a_label() -> None:
    logql = build_logql(service="tenent", tenant_id="abc-123")
    assert logql == '{service="tenent"} | json | tenant_id="abc-123"'


def test_build_logql_user_id_and_tenant_id_combine() -> None:
    logql = build_logql(tenant_id="t1", user_id="u1")
    assert logql == '{service=~".+"} | json | tenant_id="t1" | user_id="u1"'


def test_build_logql_free_text_is_a_line_filter_before_json_parsing() -> None:
    logql = build_logql(service="tenent", query_text="timeout")
    assert logql == '{service="tenent"} |= "timeout"'


def test_build_logql_escapes_quotes_in_label_values() -> None:
    logql = build_logql(service='ten"ent')
    assert logql == '{service="ten\\"ent"}'


def test_build_logql_rejects_double_quote_in_free_text() -> None:
    with pytest.raises(InvalidLogQLError):
        build_logql(query_text='has "quotes"')


def test_parse_streams_extracts_json_body_fields() -> None:
    data = {
        "data": {
            "result": [
                {
                    "stream": {"service": "tenent", "level": "ERROR"},
                    "values": [
                        [
                            "1700000000000000000",
                            (
                                '{"time":"2024-01-01T00:00:00","level":"ERROR",'
                                '"service":"tenent","message":"boom",'
                                '"tenant_id":"t1","user_id":"u1",'
                                '"trace_id":"abc","span_id":"def"}'
                            ),
                        ]
                    ],
                }
            ]
        }
    }
    entries = parse_streams(data)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.message == "boom"
    assert entry.tenant_id == "t1"
    assert entry.user_id == "u1"
    assert entry.trace_id == "abc"
    assert entry.span_id == "def"
    assert entry.service == "tenent"
    assert entry.level == "ERROR"


def test_parse_streams_falls_back_to_raw_line_for_non_json() -> None:
    data = {
        "data": {
            "result": [
                {
                    "stream": {"service": "tenent"},
                    "values": [["1700000000000000000", "not json"]],
                }
            ]
        }
    }
    entries = parse_streams(data)
    assert entries[0].message == "not json"


def test_parse_streams_sorts_newest_first() -> None:
    data = {
        "data": {
            "result": [
                {
                    "stream": {"service": "tenent"},
                    "values": [
                        ["100", "{}"],
                        ["300", "{}"],
                        ["200", "{}"],
                    ],
                }
            ]
        }
    }
    entries = parse_streams(data)
    assert [e.timestamp_ns for e in entries] == ["300", "200", "100"]
