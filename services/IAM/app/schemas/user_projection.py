from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectionMetadataSchema(BaseModel):
    """
    Common metadata shared by event-driven read models.

    Purpose:
        Provides synchronization and lifecycle metadata for
        projection entities maintained through asynchronous
        domain events.

    Notes:
        - Values are managed internally by projection consumers.
        - Clients should treat these fields as read-only.
        - Used primarily for auditing, troubleshooting,
          and replay operations.
    """

    #: Identifier of the most recent domain event successfully
    #: applied to this projection.
    #:
    #: Purpose:
    #:     - Correlate projection state with upstream events.
    #:     - Simplify distributed tracing.
    #:     - Assist operational debugging.
    #:
    #: Example:
    #:     3b06f1cb-69a5-4d8f-9b0a-74db2af27f83
    source_event_id: UUID | None = Field(
        default=None,
        description="Identifier of the last processed domain event.",
    )

    #: Monotonically increasing event version originating
    #: from the source service.
    #:
    #: Used to prevent:
    #:     - duplicate message deliveries
    #:     - replay conflicts
    #:     - out-of-order updates
    #:
    #: Example:
    #:     current_version = 7
    #:     incoming_version = 6
    #:
    #:     -> ignore stale event
    source_event_version: int | None = Field(
        default=None,
        ge=1,
        description="Version number of the last successfully applied event.",
    )

    #: Timestamp indicating when this projection record
    #: was first created inside the local service.
    #:
    #: Important:
    #:     This is NOT the upstream entity creation timestamp.
    #:
    #: Useful for:
    #:     - projection rebuild analysis
    #:     - operational metrics
    #:     - troubleshooting
    created_at: datetime = Field(
        description="Local projection creation timestamp.",
    )

    #: Timestamp of the most recent successful synchronization.
    #:
    #: Updated whenever:
    #:     - entity update events are processed
    #:     - replay operations occur
    #:     - delete events are applied
    #:
    #: This timestamp belongs to the projection itself and
    #: should not be confused with the upstream entity's
    #: updated_at value.
    updated_at: datetime = Field(
        description="Local projection update timestamp.",
    )

    #: Indicates whether the projection has been soft deleted.
    #:
    #: Reasons for retaining deleted records:
    #:     - preserve audit history
    #:     - maintain access review integrity
    #:     - support forensic investigations
    #:     - avoid orphaned references
    #:
    #: Recommended:
    #:     Prefer soft deletion over physical removal.
    is_deleted: bool = Field(
        default=False,
        description="Whether the projection has been marked as deleted.",
    )

    #: Timestamp indicating when the projection entered
    #: the deleted state.
    #:
    #: Set when processing deletion events.
    #:
    #: Remains None for active records.
    #:
    #: Useful for:
    #:     - historical reporting
    #:     - delayed cleanup jobs
    #:     - forensic analysis
    deleted_at: datetime | None = Field(
        default=None,
        description="Timestamp when the projection was soft deleted.",
    )
