"""Synthetic, computed-not-stored IDs for `GET /api/v1/logs/{id}`.

Loki has no concept of a stable per-line ID (see services/Logging/TODO.md,
Decision #4). Rather than storing one, we encode enough information in the
ID itself to rebuild a tight, targeted LogQL query and verify the line we
find is the one the caller meant:

    id = base64url(json({"s": service, "l": level, "ts": timestamp_ns, "h": line_hash}))

`service`/`level` rebuild the stream selector, `ts` narrows the query window
to a few seconds around the original timestamp, and `h` (a short hash of the
raw line) is checked against every candidate line in that window so an ID
never silently resolves to the wrong log entry.
"""

from __future__ import annotations

import base64
import hashlib
import json

from app.domain.exceptions import InvalidLogIdError


def _line_hash(raw_line: str) -> str:
    return hashlib.sha256(raw_line.encode("utf-8")).hexdigest()[:16]


def encode_log_id(
    *, service: str | None, level: str | None, timestamp_ns: str, raw_line: str
) -> str:
    payload = {
        "s": service,
        "l": level,
        "ts": timestamp_ns,
        "h": _line_hash(raw_line),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_log_id(log_id: str) -> dict[str, str | None]:
    padded = log_id + "=" * (-len(log_id) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload: dict[str, str | None] = json.loads(raw)
        if "ts" not in payload or "h" not in payload:
            raise ValueError("missing required fields")
    except Exception as exc:
        raise InvalidLogIdError(f"Could not decode log id: {exc}") from exc
    return payload


def matches_log_id(log_id_payload: dict[str, str | None], raw_line: str) -> bool:
    return log_id_payload.get("h") == _line_hash(raw_line)
