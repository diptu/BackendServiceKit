"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.session import Session

__all__ = ["Session"]
