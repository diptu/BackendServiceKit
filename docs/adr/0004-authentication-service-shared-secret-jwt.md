# 0004. Authentication issues shared-secret JWTs; refresh tokens are opaque and revocable

Date: 2026-07-06
Status: Accepted

## Context

Nothing in this repo verified identity anywhere in the request path —
`APIGateway` forwarded a client-supplied `X-Tenant-ID` with no
authentication behind it (see ADR 0006). A new `Authentication` service
was needed, and `services/Tenent`'s `IsolationService.resolve_context`
already existed, decoding a JWT with `tenant_id`/`user_id`/`scopes` claims
— written before any issuer for that token existed.

## Decision

- Access tokens are short-lived (15 min default), stateless JWTs signed
  HS256 with a secret shared between Authentication (issuer) and
  APIGateway (verifier) — matching the exact claim shape Tenent's
  `resolve_context` already expected, so it's a drop-in issuer for that
  pre-existing consumer.
- Refresh tokens and password-reset tokens are opaque
  `secrets.token_urlsafe(32)` strings, hashed at rest (SHA-256), never a
  JWT — so they can be revoked server-side. Refresh-token reuse (presenting
  an already-rotated or already-logged-out token) is treated as
  compromise: it revokes every other active session for that user, not
  just the one presented.
- Credentials (password hashes) live only in Authentication's `Credential`
  table — IAM's `UserProjection` and User's own `User` model both
  explicitly never store passwords.

## Consequences

- HS256 with a shared secret is a real limitation, not an oversight —
  every service holding the secret can *forge* tokens, not just verify
  them. A production deployment should move to asymmetric RS256 signing so
  only Authentication ever holds the private key. Tracked in
  `services/Authentication/TODO.md`, not fixed yet.
- `POST /auth/credentials` (sets a user's initial password) has no auth
  gate of its own — it has to be callable before any session exists. This
  repo has no service-to-service trust mechanism (mTLS, signed service
  tokens) yet to restrict it to trusted internal callers only. Flagged as
  the single biggest concrete gap in this service.
- MFA, OAuth2.1/OIDC, and SSO are documented in
  `services/Authentication/README.md`'s original design doc but not built
  — they need real external integration work that doesn't make sense to
  fake with placeholder tables.
