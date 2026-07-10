"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.avatar import Avatar
from app.models.contact_info import ContactInfo
from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.models.user_preferences import UserPreferences
from app.models.user_profile import UserProfile
from app.models.user_status_history import UserStatusHistory

__all__ = [
    "Avatar",
    "ContactInfo",
    "User",
    "UserInvitation",
    "UserPreferences",
    "UserProfile",
    "UserStatusHistory",
]
