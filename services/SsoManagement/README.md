# Single Sign-On (SSO) Service

## Responsibility
Allows users to authenticate using external Identity Providers (IdPs).

## Examples
* Google
* Microsoft Entra ID
* Okta
* Ping Identity

## Protocols
* SAML 2.0
* OIDC Federation

## APIs

### Provider Configuration
* `POST   /sso/providers`
* `GET    /sso/providers`
* `GET    /sso/providers/{provider_id}`
* `PATCH  /sso/providers/{provider_id}`
* `DELETE /sso/providers/{provider_id}`
* `POST   /sso/providers/{provider_id}/enable`
* `POST   /sso/providers/{provider_id}/disable`

### Authentication Flow
* `GET    /sso/login`
* `POST   /sso/acs`
* `GET    /sso/metadata`