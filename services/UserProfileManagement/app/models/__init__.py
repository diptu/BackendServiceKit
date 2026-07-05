"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.avatar import Avatar
from app.models.contact_info import ContactInfo
from app.models.user_preferences import UserPreferences
from app.models.user_profile import UserProfile

__all__ = ["Avatar", "ContactInfo", "UserPreferences", "UserProfile"]
