"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.models.user_status_history import UserStatusHistory

__all__ = ["User", "UserInvitation", "UserStatusHistory"]
