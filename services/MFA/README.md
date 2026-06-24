# Multi-Factor Authentication (MFA) Service

## Responsibility
Provides an additional authentication factor beyond password.

## Factors
* TOTP (Authenticator App)
* SMS OTP
* Email OTP
* Passkeys
* Security Keys

## APIs

### Setup & Verification
* `POST /mfa/setup`
* `POST /mfa/verify`
* `POST /mfa/challenge`
* `POST /mfa/disable`

### Recovery & Status
* `POST /mfa/recovery-codes`
* `GET  /mfa/status`

### Passkeys
* `POST   /mfa/passkeys/register`
* `POST   /mfa/passkeys/verify`
* `DELETE /mfa/passkeys/{id}`