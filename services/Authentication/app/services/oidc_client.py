"""OIDC relying-party client — the piece that actually talks to an external
identity provider.

It is an abstract seam on purpose: `SsoService` depends only on the
`OidcClient` interface, so the real `HttpxOidcClient` (which performs the
authorization-code exchange and validates the returned id_token against the
IdP's published JWKS) can be swapped for a fake in tests without any network
access. Building the real client requires a fully configured provider
(issuer, client id/secret, endpoints, redirect_uri); if any of that is
missing, construction raises `SsoNotConfiguredError` rather than half-working.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt  # type: ignore[import-untyped]

from app.core.config import settings
from app.domain.exceptions import SsoNotConfiguredError, SsoStateInvalidError


class OidcClaims(TypedDict):
    subject: str
    email: str


class OidcProviderConfig:
    __slots__ = (
        "issuer",
        "client_id",
        "client_secret",
        "authorization_endpoint",
        "token_endpoint",
        "jwks_uri",
        "redirect_uri",
    )

    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        client_secret: str,
        authorization_endpoint: str,
        token_endpoint: str,
        jwks_uri: str,
        redirect_uri: str,
    ) -> None:
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.jwks_uri = jwks_uri
        self.redirect_uri = redirect_uri


def load_provider_config() -> OidcProviderConfig:
    required = {
        "oidc_issuer": settings.oidc_issuer,
        "oidc_client_id": settings.oidc_client_id,
        "oidc_client_secret": settings.oidc_client_secret,
        "oidc_authorization_endpoint": settings.oidc_authorization_endpoint,
        "oidc_token_endpoint": settings.oidc_token_endpoint,
        "oidc_jwks_uri": settings.oidc_jwks_uri,
        "oidc_redirect_uri": settings.oidc_redirect_uri,
    }
    if any(v is None for v in required.values()):
        raise SsoNotConfiguredError()
    return OidcProviderConfig(
        issuer=str(settings.oidc_issuer),
        client_id=str(settings.oidc_client_id),
        client_secret=str(settings.oidc_client_secret),
        authorization_endpoint=str(settings.oidc_authorization_endpoint),
        token_endpoint=str(settings.oidc_token_endpoint),
        jwks_uri=str(settings.oidc_jwks_uri),
        redirect_uri=str(settings.oidc_redirect_uri),
    )


class OidcClient(ABC):
    @property
    @abstractmethod
    def redirect_uri(self) -> str: ...

    @abstractmethod
    def authorization_url(self, *, state: str, nonce: str) -> str: ...

    @abstractmethod
    async def exchange_and_verify(
        self, *, code: str, redirect_uri: str, nonce: str
    ) -> OidcClaims: ...


class HttpxOidcClient(OidcClient):
    def __init__(self, config: OidcProviderConfig) -> None:
        self._config = config

    @property
    def redirect_uri(self) -> str:
        return self._config.redirect_uri

    def authorization_url(self, *, state: str, nonce: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
        }
        return f"{self._config.authorization_endpoint}?{urlencode(params)}"

    async def exchange_and_verify(
        self, *, code: str, redirect_uri: str, nonce: str
    ) -> OidcClaims:
        async with httpx.AsyncClient(timeout=10.0) as http:
            token_resp = await http.post(
                self._config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                },
            )
            if token_resp.status_code != 200:
                raise SsoStateInvalidError()
            id_token = token_resp.json().get("id_token")
            if not id_token:
                raise SsoStateInvalidError()

            jwks_resp = await http.get(self._config.jwks_uri)
            jwks = jwks_resp.json()

        try:
            claims = jwt.decode(
                id_token,
                jwks,
                algorithms=["RS256", "ES256"],
                audience=self._config.client_id,
                issuer=self._config.issuer,
            )
        except JWTError as exc:
            raise SsoStateInvalidError() from exc

        if claims.get("nonce") != nonce:
            raise SsoStateInvalidError()
        subject = claims.get("sub")
        email = claims.get("email")
        if not subject or not email:
            raise SsoStateInvalidError()
        return OidcClaims(subject=str(subject), email=str(email))
