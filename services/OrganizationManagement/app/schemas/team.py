"""Pydantic schemas for Team/Department endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import TeamStatus, TeamType
from app.schemas.base import AppBaseModel


class CreateTeamRequest(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    team_type: TeamType = TeamType.TEAM
    parent_team_id: UUID | None = None


class UpdateTeamRequest(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class TeamResponse(AppBaseModel):
    id: UUID
    organization_id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    team_type: TeamType
    parent_team_id: UUID | None
    status: TeamStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class TeamListResponse(AppBaseModel):
    items: list[TeamResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False


class AddTeamMemberRequest(AppBaseModel):
    user_id: UUID


class TeamMemberListResponse(AppBaseModel):
    items: list[UUID]
    total: int
