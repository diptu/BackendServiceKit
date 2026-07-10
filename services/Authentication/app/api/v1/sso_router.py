"""SSO (OIDC) endpoints — this service as a relying party to an external IdP.

`POST /sso/login` returns the IdP authorization URL to redirect the user to;
`POST /sso/callback` completes the code exchange, validates the id_token, maps
the federated identity to a local account, and issues this service's own
tokens. Both 503 if no IdP is configured (see get_sso_service).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.v1.dependencies import SsoServiceDep, TenantIdDep
from app.core.config import settings
from app.domain.exceptions import (
    SsoIdentityNotProvisionedError,
    SsoStateInvalidError,
)
from app.schemas.sso import SsoCallbackRequest, SsoLoginResponse, SsoTokenResponse

router = APIRouter(prefix="/sso", tags=["SSO"])


@router.post("/login", response_model=SsoLoginResponse)
async def sso_login(tenant_id: TenantIdDep, svc: SsoServiceDep) -> SsoLoginResponse:
    url = await svc.begin_login(tenant_id)
    return SsoLoginResponse(authorization_url=url)


@router.post("/callback", response_model=SsoTokenResponse)
async def sso_callback(
    body: SsoCallbackRequest, tenant_id: TenantIdDep, svc: SsoServiceDep
) -> SsoTokenResponse:
    try:
        pair = await svc.complete_login(tenant_id, code=body.code, state=body.state)
    except SsoStateInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SsoIdentityNotProvisionedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return SsoTokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )
