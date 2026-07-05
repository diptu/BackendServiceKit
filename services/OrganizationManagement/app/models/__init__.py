"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.organization import Organization
from app.models.organization_event import OrganizationEvent
from app.models.organization_invitation import OrganizationInvitation
from app.models.organization_membership import OrganizationMembership
from app.models.organization_settings import OrganizationSettings
from app.models.organization_settings_history import OrganizationSettingsHistory
from app.models.organization_team import OrganizationTeam, TeamMembership

__all__ = [
    "Organization",
    "OrganizationEvent",
    "OrganizationInvitation",
    "OrganizationMembership",
    "OrganizationSettings",
    "OrganizationSettingsHistory",
    "OrganizationTeam",
    "TeamMembership",
]
