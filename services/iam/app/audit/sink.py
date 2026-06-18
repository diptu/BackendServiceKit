import json
import logging

from app.audit.events import AuditEvent

_logger = logging.getLogger("iam.audit")


class StdoutSink:
    """Emits structured JSON audit records to the iam.audit logger stream."""

    def emit(self, event: AuditEvent) -> None:
        record = {
            "timestamp": event.timestamp.isoformat(),
            "event": str(event.event_type),
            "user_id": event.user_id,
            "email": event.email,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "jti": event.jti,
            "detail": event.detail,
        }
        _logger.info(json.dumps(record))
