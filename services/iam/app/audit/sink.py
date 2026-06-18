import structlog

from app.audit.events import AuditEvent

_log = structlog.get_logger("iam.audit")


class StdoutSink:
    """Emits structured JSON audit records via structlog."""

    def emit(self, event: AuditEvent) -> None:
        _log.info(
            str(event.event_type),
            timestamp=event.timestamp.isoformat(),
            user_id=event.user_id,
            email=event.email,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            jti=event.jti,
            detail=event.detail,
        )
