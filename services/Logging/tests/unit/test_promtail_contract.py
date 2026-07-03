"""Pins the one seam where a change to shared/observability could silently
break the whole log pipeline: promtail's `pipeline_stages` (see
services/Logging/promtail/promtail-config.yaml) parses `level`, `trace_id`,
`span_id`, `service`, `message` out of each JSON log line. If
OTelJSONFormatter ever stops emitting one of these top-level keys, promtail's
`json:` stage silently produces empty values instead of failing loudly.
"""

from __future__ import annotations

import json
import logging

from shared.observability.logging.json_formatter import OTelJSONFormatter

_PROMTAIL_EXPECTED_KEYS = {"level", "trace_id", "span_id", "service", "message"}


def test_formatter_output_has_every_key_promtail_extracts() -> None:
    formatter = OTelJSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="boom",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))
    assert _PROMTAIL_EXPECTED_KEYS.issubset(payload.keys())


def test_formatter_output_is_valid_json_on_one_line() -> None:
    formatter = OTelJSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    line = formatter.format(record)
    assert "\n" not in line
    payload = json.loads(line)
    assert payload["message"] == "hello world"
