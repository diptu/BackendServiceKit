"""Application-level Pydantic base model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """Shared base for all request and response schemas in this service."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
    )
