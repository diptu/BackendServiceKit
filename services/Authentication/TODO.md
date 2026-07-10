# Authentication — Implementation Notes

## Siloed Multi-tenancy (database-per-tenant) — opt-in

Supports the platform's Siloed multi-tenancy standard, mirroring IAM (the
reference implementation — see `services/IAM/TODO.md`):

- `get_db` (`app/infrastructure/database/dependencies.py`) routes each request
  to its tenant's own database when `siloed_multitenancy_enabled`, failing
  closed (400) if no `X-Tenant-ID` is present. Default OFF → shared-schema
  unchanged.
- `app/infrastructure/database/tenant_routing.py` builds the shared
  `TenantEngineRegistry` (`shared/db/`); `tenant_resolver` selects the dev
  `template` resolver or the production `control_plane` resolver (fetches each
  tenant's DSN from Tenent). Config flags in `app/core/config.py`.
- Per-tenant migrations: `alembic/env.py` accepts a target URL;
  `scripts/tenant_migrations.py` applies `upgrade head` across tenant DBs
  (verified end-to-end: two tenant DBs, 12 tables incl. `credentials`, each
  isolated). **Siloing fits this service cleanly**: the subdomain/gateway
  resolves the tenant *before* credentials are checked, so login hits the
  right tenant database; the `(tenant_id, email)` composite becomes a
  per-database `email` uniqueness.
- Verified: 59/59 tests (12 in `tests/unit/test_siloed_multitenancy.py`); ruff
  clean; 0 new mypy errors.

Blocked (not this service's to build): physical `CREATE DATABASE`/drop on
tenant provisioning/offboarding (Tenent + infra), PgBouncer, secrets backend.

**Status: v2 implemented.** v1 (credential storage, login, JWT access
tokens, rotating/revocable refresh tokens, account lockout, password
change/reset, session listing/revocation, append-only audit log) plus v2:
MFA (TOTP with recovery codes + login step-up), OAuth 2.1 authorization-code
grant with PKCE, SSO via OIDC, and optional RS256 asymmetric token signing
with a published JWKS. 47/47 tests pass against SQLite; no Postgres
deployment has been run against a live container yet (unlike User/Tenent's
TODO.md, which both describe real Docker end-to-end verification — that step
is still outstanding here).

## Why this exists

This was built to close the single largest gap this repo's own
production-readiness audit found: nothing verified identity anywhere in the
request path. APIGateway forwarded a client-supplied `X-Tenant-ID` header
with no authentication behind it, so every tenant-scoping check downstream
(IAM, User, Tenent) was enforcing a boundary the caller could simply
declare its way around.

## What's built vs what README.md still only describes

README.md is this service's original design doc and — per this repo's own
convention (see IAM's README, which is equally unmodified despite IAM being
fully built) — it stays as the aspirational spec rather than being edited
down to "current state." This file is where that distinction actually
lives:

**Built (v1):** `POST /auth/credentials` (set initial password), `POST
/auth/login`, `POST /auth/refresh`, `POST /auth/logout` + `POST
/auth/revoke` (same operation, kept as two routes since the design doc
lists both verbs), `POST /auth/logout-all`, `POST /auth/introspect`, `POST
/auth/password/change` (authenticated), `POST /auth/password/forgot` +
`POST /auth/password/reset`, `GET /auth/sessions` + `DELETE
/auth/sessions/{id}`, `GET /auth/events` (audit trail — not in the
original design doc, added because `AuthEvent` needed a read path).

**Built (v2):**

- **MFA (TOTP):** `POST /auth/mfa/setup` (enroll → secret + provisioning URI
  + 10 one-time recovery codes), `POST /auth/mfa/activate` (confirm
  possession before MFA is enforced — added beyond the 3-endpoint design
  doc for a proper two-phase enrollment, same convention as `/auth/events`),
  `POST /auth/mfa/verify` (public login step-up, authenticated by a
  single-use `mfa_token` rather than a Bearer token), `POST
  /auth/mfa/disable`. When MFA is enabled, `/auth/login` returns
  `{mfa_required: true, mfa_token}` instead of tokens. WebAuthn is still not
  built (TOTP only).
- **OAuth 2.1:** `GET /oauth/authorize` (authorization-code, resource owner
  authenticated by a Bearer token this service issued), `POST /oauth/token`
  (`authorization_code` with mandatory-for-public-clients PKCE/S256, plus
  `refresh_token` grant), `POST /oauth/clients` (dynamic registration —
  carries the same trust caveat as `/auth/credentials`, see below). Implicit
  and password grants are intentionally omitted per OAuth 2.1.
- **SSO (OIDC):** `POST /sso/login` (returns the IdP authorization URL),
  `POST /sso/callback` (code exchange + id_token validation via the injected
  `OidcClient`, then maps the federated identity to a local account). No
  just-in-time provisioning — an identity with no matching local credential
  is refused (403), because the User service, not this one, owns identity
  creation.
- **RS256 signing:** opt-in via `jwt_algorithm=RS256` + a PEM keypair; tokens
  then carry a `kid` and the public key is published at
  `GET /.well-known/jwks.json`. HS256 stays the default.

**Still not built — WebAuthn/passkeys, SAML SSO, and true SCIM/JIT user
provisioning from the SSO callback** (needs the User service integration).

## Design decisions worth recording

1. **This is the only place a password hash exists in the platform.** IAM's
   `UserProjection` and the `User` service's own `User` model both
   explicitly never store passwords or MFA secrets — this service is where
   that boundary lands. `Credential.user_id` is a projection reference
   (plain column, not a FK), same convention this repo already uses
   whenever a reference crosses a service's own database boundary.

2. **Access tokens are stateless JWTs; refresh and password-reset tokens
   are opaque, hashed-at-rest, server-revocable strings** — never JWTs.
   The access-token claim shape (`tenant_id`, `user_id`, `scopes`) is not
   arbitrary: it's the exact shape `Tenent`'s `IsolationService.resolve_context`
   already expects to decode (that endpoint existed before this service
   did, waiting for an issuer). Both currently sign/verify with the same
   `SECRET_KEY` (HS256) by default. **RS256 is now supported** — set
   `jwt_algorithm=RS256` plus a PEM `jwt_private_key`/`jwt_public_key` pair
   and only this service holds the private key; every other service verifies
   with the public key it fetches from `GET /.well-known/jwks.json`
   (`get_jwks()` returns an empty key set under HS256, since a shared secret
   is never published). The default stays HS256 so existing shared-secret
   consumers keep working until they migrate.

3. **Refresh-token reuse is treated as compromise, not just an invalid
   request.** Rotating a refresh token revokes the old one and records
   `replaced_by`; presenting an already-rotated (or already-logged-out)
   token again revokes every other active session for that user, not just
   the one presented. This is the standard mitigation for refresh-token
   replay, and it's the reason `refresh()` and `logout()` don't just return
   404/401 on an unknown hash — they actively distrust the rest of that
   user's sessions when the signal looks like theft rather than expiry.

4. **Every failure path returns the identical `InvalidCredentialsError`**
   whether the email is unknown or the password is wrong. No code path
   anywhere distinguishes the two in an HTTP response — the Authentication
   skill this service was built against is explicit that failure detail
   leakage is what makes credential stuffing/enumeration attacks cheap.

5. **`POST /auth/credentials` has no auth gate of its own.** It has to be
   callable before any session exists (nothing else stores a password to
   check against), but that means it's currently reachable by anyone who
   can reach the service at all. This repo has no service-to-service trust
   mechanism yet (mTLS, signed service tokens) to restrict it to "only the
   User service's invitation-accept flow may call this." Flagged as the
   biggest concrete gap in this build — do not expose this route publicly
   through the gateway without addressing it first. **`POST /oauth/clients`
   (dynamic client registration) has the identical caveat** and must be
   locked down the same way.

6. **`/auth/password/forgot` always returns the same response shape**
   regardless of whether the email is registered (no enumeration), and
   only returns the raw reset token in the body when
   `ENVIRONMENT != production`. There is no NotificationService in this
   repo yet to deliver it out-of-band by email — in production today this
   endpoint silently doesn't deliver the token anywhere. That's a real gap,
   not an oversight; building NotificationService is a prerequisite for
   this endpoint to be production-usable.

7. **Rate limiting is actually applied, not just wired.** `Tenent`'s
   `rate_limit.py` sets up a `slowapi.Limiter` as middleware but never adds
   `@limiter.limit(...)` to any route, so it's currently inert there. This
   service's `/auth/login` genuinely has `@limiter.limit("5/minute")` on
   it, per the Authentication skill's explicit "rate limit login endpoints"
   principle.

8. **Audit log ordering uses the same `seq`-int-primary-key pattern as
   User's `UserStatusHistory`,** for the same reason: `occurred_at` alone
   isn't reliable ordering under SQLite's second-resolution timestamps, and
   a plain auto-incrementing integer is portable across SQLite and
   Postgres where a UUID isn't. `id` stays a separate unique UUID for
   external reference.

## Verification

1. `uv sync`, `uv run pytest -v` — 47/47 passing. v1 (25): credential
   creation (incl. cross-tenant email collision is *not* a conflict — same
   email across two tenants is fine, only same-tenant duplicates are
   rejected), login (success, generic-401 on both wrong-password and
   unknown-email, cross-tenant login rejected, account lockout after 5
   failed attempts), refresh (rotation, replay-of-a-rotated-token revokes
   the whole chain), logout (idempotent, logout-all kills every session),
   password change/forgot/reset (including reset-token single-use), sessions
   (list, revoke-own, cross-user revoke is a silent no-op rather than a
   404 that would leak the session's existence), introspection (valid →
   active claims, garbage → `active: false`, never an error status). v2 (22):
   MFA enrollment/activation, login step-up, single-use recovery codes,
   disable-restores-plain-login, already-enabled conflict; OAuth full
   authorization-code+PKCE flow (issued token is introspectable), PKCE
   mismatch, single-use codes, public-client-requires-PKCE, bad client
   secret, unauthenticated authorize, refresh grant; SSO federated login
   matched to a local account, unprovisioned identity refused, invalid and
   single-use state; RS256 round-trip + kid header + JWKS publication + a
   shared-secret verifier being unable to validate an RS256 token.
2. `ruff check` / `ruff format --check` clean.
3. `mypy --strict`: 10 errors, all the same shape every sibling service
   accepts (`shared.observability.*` stubs not implemented yet, two
   pre-existing `type: ignore` quirks in copied boilerplate, one
   `conftest.py` type-var note) — nothing new introduced by v2.
4. Both migrations (`f1a2b3c4d5e6` → `a1b2c3d4e5f6`) verified to
   `alembic upgrade head` and `downgrade base` cleanly against SQLite.
5. **Not yet done:** real Postgres + Docker end-to-end verification (the
   standard this repo holds every other service to before calling it done —
   see User's and Tenent's TODO.md for what that looked like there). Both
   Alembic migrations are hand-written to match the ORM models rather than
   autogenerated against a live database — re-verify against a real
   `nutratenant_authentication` Postgres database before trusting this
   service in any shared environment.

## Follow-up work (not done in this build)

- WebAuthn/passkeys as a second MFA factor (TOTP is done); SAML SSO
  alongside the OIDC relying-party flow that is done.
- True JIT/SCIM user provisioning from the SSO callback — today an SSO login
  for an email with no local credential is refused rather than creating the
  user, because the User service owns identity creation.
- Service-to-service trust (mTLS or signed service tokens) so
  `/auth/credentials` **and `/oauth/clients`** can be locked down to trusted
  internal callers only.
- NotificationService integration so `/auth/password/forgot` can actually
  deliver a reset link instead of returning the token directly outside
  production.
- Real Postgres + Docker verification (see above).
