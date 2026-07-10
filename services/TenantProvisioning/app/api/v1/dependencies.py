"""FastAPI shared dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.control_plane import (
    ControlPlaneRegistrar,
    HttpxControlPlaneRegistrar,
    NullControlPlaneRegistrar,
)
from app.infrastructure.database.dependencies import get_db
from app.infrastructure.provisioner import build_provisioner
from app.services.migration_runner import MarkerMigrationRunner
from app.services.provisioning_service import ProvisioningService


def _build_registrar() -> ControlPlaneRegistrar:
    if not settings.control_plane_register_enabled:
        return NullControlPlaneRegistrar()
    return HttpxControlPlaneRegistrar(
        settings.control_plane_base_url, timeout=settings.control_plane_timeout
    )


async def get_provisioning_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProvisioningService:
    return ProvisioningService(
        db,
        build_provisioner(),
        MarkerMigrationRunner(),
        _build_registrar(),
    )


ProvisioningServiceDep = Annotated[
    ProvisioningService, Depends(get_provisioning_service)
]
