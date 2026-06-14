"""
Async-safe initialization for database models.
"""

# Ensure all models are imported so they are registered with Base
import app.models  # noqa: F401


def import_all_models() -> None:
    """
    Ensure all SQLAlchemy models are imported before
    metadata/table creation.
    """

    import app.models.user
    import app.models.UserProfile  # noqa: F401
