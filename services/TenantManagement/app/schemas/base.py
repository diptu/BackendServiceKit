"""Application-level Pydantic base model.

All service schemas should inherit from ``AppBaseModel`` rather than
``pydantic.BaseModel`` directly. This gives a single place to tune global
serialization behaviour (aliases, enum coercion, etc.) without touching
every schema file.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """Shared base for all request and response schemas in this service."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
    )
