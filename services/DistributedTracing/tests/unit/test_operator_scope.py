from __future__ import annotations

import pytest

from app.api.v1.dependencies import require_operator_scope
from app.core.config import settings
from app.domain.exceptions import NotAnOperatorError


async def test_auth_disabled_allows_anyone() -> None:
    assert settings.jwt_auth_enabled is False
    await require_operator_scope(claims={})


async def test_missing_role_rejected_when_auth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_auth_enabled", True)
    with pytest.raises(NotAnOperatorError):
        await require_operator_scope(claims={"roles": ["some-other-role"]})


async def test_platform_admin_role_allowed_when_auth_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_auth_enabled", True)
    await require_operator_scope(claims={"roles": ["platform-admin"]})
