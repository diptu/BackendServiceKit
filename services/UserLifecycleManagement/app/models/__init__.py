"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.lifecycle_event import LifecycleEvent
from app.models.lifecycle_state import LifecycleState

__all__ = ["LifecycleEvent", "LifecycleState"]
