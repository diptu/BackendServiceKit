# Password Management Service

## Responsibility
Manages passwords and password policies.

## Scope
* Change password
* Reset password
* Forgot password
* Password history
* Password expiration
* Password policy enforcement

## APIs

### Change Password
* `POST /password/change`

### Forgot & Reset Password
* `POST /password/forgot`
* `POST /password/reset`

### Validation & Policy
* `POST /password/validate`
* `GET  /password/policy`
* `PATCH /password/policy`

### History & Expiration
* `GET  /password/history`
* `POST /password/expire`
* `POST /password/unexpire`