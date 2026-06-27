"""Pydantic request/response schemas for lifecycle resources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.constants import TRANSITION_REASON_MAX_LENGTH
from app.domain.enums import TenantLifecycleStatus
from app.schemas.base import AppBaseModel

_EX_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
_EX_USER_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
_EX_EVENT_ID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"


class TransitionRequest(AppBaseModel):
    """Optional body for lifecycle transition endpoints."""

    reason: str | None = Field(
        default=None,
        max_length=TRANSITION_REASON_MAX_LENGTH,
        description="Human-readable reason for the transition.",
        examples=["Non-payment — subscription expired 2026-06-01."],
    )
    performed_by: UUID | None = Field(
        default=None,
        description="UUID of the actor triggering this transition. Omit for system actions.",
        examples=[_EX_USER_ID],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "reason": "Non-payment — subscription expired 2026-06-01.",
                "performed_by": _EX_USER_ID,
            }
        },
    )


class LifecycleStateResponse(AppBaseModel):
    """Current lifecycle state for a tenant."""

    tenant_id: UUID
    current_status: TenantLifecycleStatus
    previous_status: TenantLifecycleStatus | None
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "tenant_id": _EX_TENANT_ID,
                "current_status": "active",
                "previous_status": "provisioning",
                "updated_at": "2026-06-01T12:00:00Z",
            }
        },
    )


class LifecycleEventResponse(AppBaseModel):
    """A single lifecycle transition event record."""

    id: UUID
    tenant_id: UUID
    from_status: str | None
    to_status: str
    transition: str
    reason: str | None
    performed_by: UUID | None
    source: str
    occurred_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EX_EVENT_ID,
                "tenant_id": _EX_TENANT_ID,
                "from_status": "provisioning",
                "to_status": "active",
                "transition": "activate",
                "reason": None,
                "performed_by": _EX_USER_ID,
                "source": "api",
                "occurred_at": "2026-06-01T12:00:00Z",
            }
        },
    )


class LifecycleHistoryResponse(AppBaseModel):
    """Paginated list of lifecycle events for a tenant."""

    tenant_id: UUID
    events: list[LifecycleEventResponse]
    total: int = Field(..., description="Total number of events.", examples=[5])
    has_more: bool = Field(..., description="Whether additional pages are available.")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "tenant_id": _EX_TENANT_ID,
                "events": [
                    {
                        "id": _EX_EVENT_ID,
                        "tenant_id": _EX_TENANT_ID,
                        "from_status": "provisioning",
                        "to_status": "active",
                        "transition": "activate",
                        "reason": None,
                        "performed_by": None,
                        "source": "api",
                        "occurred_at": "2026-06-01T12:00:00Z",
                    }
                ],
                "total": 1,
                "has_more": False,
            }
        },
    )
