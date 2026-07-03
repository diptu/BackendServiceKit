from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidLogIdError
from app.domain.log_id import decode_log_id, encode_log_id, matches_log_id


def test_encode_decode_roundtrip() -> None:
    log_id = encode_log_id(
        service="tenent",
        level="ERROR",
        timestamp_ns="1700000000000000000",
        raw_line='{"message":"boom"}',
    )
    payload = decode_log_id(log_id)
    assert payload["s"] == "tenent"
    assert payload["l"] == "ERROR"
    assert payload["ts"] == "1700000000000000000"


def test_matches_log_id_true_for_same_line() -> None:
    raw_line = '{"message":"boom"}'
    log_id = encode_log_id(service="tenent", level="ERROR", timestamp_ns="1", raw_line=raw_line)
    payload = decode_log_id(log_id)
    assert matches_log_id(payload, raw_line) is True


def test_matches_log_id_false_for_different_line() -> None:
    log_id = encode_log_id(
        service="tenent", level="ERROR", timestamp_ns="1", raw_line='{"message":"boom"}'
    )
    payload = decode_log_id(log_id)
    assert matches_log_id(payload, '{"message":"different"}') is False


def test_decode_invalid_id_raises() -> None:
    with pytest.raises(InvalidLogIdError):
        decode_log_id("not-valid-base64!!!")


def test_decode_valid_base64_missing_fields_raises() -> None:
    import base64
    import json

    bad = base64.urlsafe_b64encode(json.dumps({"foo": "bar"}).encode()).decode().rstrip("=")
    with pytest.raises(InvalidLogIdError):
        decode_log_id(bad)
