"""Minimal logging configuration."""

from __future__ import annotations

import logging


def configure_logging(*, debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)-5.5s [%(name)s] %(message)s",
    )
