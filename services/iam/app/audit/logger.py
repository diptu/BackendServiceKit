from datetime import UTC, datetime

from app.audit.events import AuditEvent, AuditEventType
from app.audit.sink import StdoutSink


class AuditLogger:
    """Facade that stamps events with UTC time and dispatches them to a sink."""

    def __init__(self, sink: StdoutSink | None = None) -> None:
        self._sink = sink or StdoutSink()

    def log(
        self,
        event_type: AuditEventType,
        *,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        user_id: str | None = None,
        jti: str | None = None,
        detail: str | None = None,
    ) -> None:
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            jti=jti,
            detail=detail,
        )
        self._sink.emit(event)
