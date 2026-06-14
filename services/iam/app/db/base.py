# app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Abstract declarative base class for all SQLAlchemy relational models.
    Registers common metadata and table reflection configurations.
    """

    pass
