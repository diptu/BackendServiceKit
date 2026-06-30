"""SQLAlchemy auto-instrumentation — spans for every SQL statement."""

from __future__ import annotations

from typing import Any


def instrument_sqlalchemy(engine: Any = None) -> None:
    """Instrument SQLAlchemy to emit OTel spans per SQL operation.

    Pass the engine to bind instrumentation to a specific engine, or omit to
    instrument all engines created after this call.
    """
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor  # type: ignore[import]

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)
    else:
        SQLAlchemyInstrumentor().instrument(enable_commenter=True)
