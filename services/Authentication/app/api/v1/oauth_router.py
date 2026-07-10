"""OAuth 2.1 endpoints — authorization-code + PKCE, with this service as the
authorization server.

`POST /oauth/clients` (dynamic registration) carries the same trust caveat as
`/auth/credentials`: it is not gated by service-to-service auth yet, so it
must not be exposed publicly through the gateway until that exists (TODO.md).
`GET /oauth/authorize` requires the resource owner to present a Bearer access
token this service already issued (a real browser deployment would front it
with an interactive login + consent screen).
"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.api.v1.dependencies import (
    AuthServiceDep,
    CurrentSubjectDep,
    OAuthServiceDep,
    TenantIdDep,
)
from app.core.config import settings
from app.domain.exceptions import OAuthInvalidRequestError, RefreshTokenInvalidError
from app.schemas.oauth import (
    OAuthTokenResponse,
    RegisterClientRequest,
    RegisterClientResponse,
    TokenRequest,
)

router = APIRouter(prefix="/oauth", tags=["OAuth2.1"])


def _oauth_error(exc: OAuthInvalidRequestError) -> HTTPException:
    status_code = 401 if exc.error == "invalid_client" else 400
    return HTTPException(
        status_code=status_code,
        detail={"error": exc.error, "error_description": exc.description},
    )


@router.post("/clients", response_model=RegisterClientResponse, status_code=201)
async def register_client(
    body: RegisterClientRequest, tenant_id: TenantIdDep, svc: OAuthServiceDep
) -> RegisterClientResponse:
    try:
        client = await svc.register_client(
            tenant_id,
            name=body.name,
            redirect_uris=body.redirect_uris,
            allowed_scopes=body.allowed_scopes,
            is_confidential=body.is_confidential,
        )
    except OAuthInvalidRequestError as exc:
        raise _oauth_error(exc) from exc
    return RegisterClientResponse(
        client_id=client.client_id,
        client_secret=client.client_secret,
        is_confidential=body.is_confidential,
    )


@router.get("/authorize")
async def authorize(
    subject: CurrentSubjectDep,
    svc: OAuthServiceDep,
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str | None = None,
    state: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> RedirectResponse:
    """On success, 302-redirects to `redirect_uri?code=...&state=...`."""
    try:
        code = await svc.authorize(
            subject["tenant_id"],
            subject["user_id"],
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
    except OAuthInvalidRequestError as exc:
        raise _oauth_error(exc) from exc

    params = {"code": code}
    if state:
        params["state"] = state
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{sep}{urlencode(params)}", status_code=302
    )


@router.post("/token", response_model=OAuthTokenResponse)
async def token(
    body: TokenRequest,
    tenant_id: TenantIdDep,
    svc: OAuthServiceDep,
    auth: AuthServiceDep,
) -> OAuthTokenResponse:
    if body.grant_type == "authorization_code":
        if not body.code or not body.redirect_uri or not body.client_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": (
                        "code, redirect_uri and client_id are required."
                    ),
                },
            )
        try:
            pair, scopes = await svc.exchange_code(
                tenant_id,
                client_id=body.client_id,
                client_secret=body.client_secret,
                code=body.code,
                redirect_uri=body.redirect_uri,
                code_verifier=body.code_verifier,
            )
        except OAuthInvalidRequestError as exc:
            raise _oauth_error(exc) from exc
        return OAuthTokenResponse(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=settings.access_token_ttl_seconds,
            scope=" ".join(scopes) if scopes else None,
        )

    if body.grant_type == "refresh_token":
        if not body.refresh_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": "refresh_token is required.",
                },
            )
        try:
            pair = await auth.refresh(tenant_id, body.refresh_token)
        except RefreshTokenInvalidError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_grant", "error_description": str(exc)},
            ) from exc
        return OAuthTokenResponse(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=settings.access_token_ttl_seconds,
        )

    raise HTTPException(
        status_code=400,
        detail={
            "error": "unsupported_grant_type",
            "error_description": f"Unsupported grant_type: {body.grant_type}.",
        },
    )
