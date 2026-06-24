# OAuth2/OpenID Connect Service

## Responsibility
Provides industry-standard token issuance and identity federation.

### OAuth2
* Authorization Framework

### OpenID Connect
* Identity Layer on top of OAuth2

## Supports
* Authorization Code Flow
* PKCE (Proof Key for Code Exchange)
* Client Credentials
* Refresh Tokens
* JWT Access Tokens

## APIs

### OAuth Clients
* `POST  /oauth/clients`
* `GET   /oauth/clients`
* `PATCH /oauth/clients/{client_id}`
* `DELETE /oauth/clients/{client_id}`

### Authorization
* `GET  /oauth/authorize`
* `POST /oauth/token`
* `POST /oauth/revoke`
* `POST /oauth/introspect`

### OIDC
* `GET  /.well-known/openid-configuration`
* `GET  /oauth/userinfo`
* `GET  /oauth/jwks`