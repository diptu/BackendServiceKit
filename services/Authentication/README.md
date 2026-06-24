# Authentication Service

Authentication only verifies identity.

Its job ends once the user is proven legitimate.

Authentication should never decide permissions.

## Responsibilities
* Login
* Logout
* Password verification
* MFA verification
* Token issuance
* Token refresh
* Session creation
* Session revocation
* SSO login
* OAuth login

## Owns
* `sessions`
* `refresh_tokens`
* `access_tokens`
* `mfa_challenges`
* `password_resets`
* `login_attempts`

## Authentication API Endpoints

### Login
* `POST /auth/login`

### Logout
* `POST /auth/logout`

### Refresh Token
* `POST /auth/refresh`

### Validate Token
* `POST /auth/introspect`

### Revoke Token
* `POST /auth/revoke`

### MFA
* `POST /auth/mfa/setup`
* `POST /auth/mfa/verify`
* `POST /auth/mfa/disable`

### Password Reset
* `POST /auth/password/forgot`
* `POST /auth/password/reset`

### Session Management
* `GET /auth/sessions`
* `DELETE /auth/sessions/{session_id}`

### OAuth
* `GET /oauth/authorize`
* `POST /oauth/token`

### SSO
* `POST /sso/login`
* `POST /sso/callback`