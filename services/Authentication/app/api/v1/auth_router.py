"""Authentication endpoints — credentials, login, tokens, sessions, password
reset. Matches the endpoint surface documented in this service's original
README.md design doc; MFA/OAuth2/SSO endpoints listed there are
intentionally not built yet — see TODO.md."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.api.v1.dependencies import (
    AuthServiceDep,
    CurrentSubjectDep,
    MfaServiceDep,
    TenantIdDep,
)
from app.core.config import settings
from app.domain.commands import (
    ChangePasswordCmd,
    LoginCmd,
    ResetPasswordCmd,
    SetCredentialCmd,
)
from app.domain.exceptions import (
    AccessTokenInvalidError,
    AccountLockedError,
    CredentialAlreadyExistsError,
    CredentialNotFoundError,
    InvalidCredentialsError,
    InvalidMfaCodeError,
    MfaAlreadyEnabledError,
    MfaNotEnrolledError,
    PasswordResetTokenInvalidError,
    RefreshTokenInvalidError,
)
from app.middleware.rate_limit import limiter
from app.services.session_issuer import AuthTokenPair
from app.schemas.auth import (
    AuthEventListResponse,
    AuthEventResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    IntrospectRequest,
    IntrospectResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    ResetPasswordRequest,
    RevokeRequest,
    SessionListResponse,
    SessionResponse,
    SetCredentialRequest,
    TokenPairResponse,
)
from app.schemas.mfa import (
    MfaActivateRequest,
    MfaDisableRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    MfaVerifyResponse,
)
from app.services.token_service import decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _pair_response(pair: AuthTokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/credentials", status_code=204)
async def set_credential(
    body: SetCredentialRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> None:
    """Sets the initial password for a user_id that already exists in the
    User service. Not gated by any auth here — in a real deployment this
    must only be reachable from a trusted internal caller (e.g. the User
    service's invitation-accept flow), not the public internet. This repo
    has no service-to-service auth (mTLS/service tokens) yet — see
    TODO.md."""
    cmd = SetCredentialCmd(
        user_id=body.user_id, email=body.email, password=body.password
    )
    try:
        await svc.set_credential(tenant_id, cmd)
    except CredentialAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.login_rate_limit)
async def login(
    request: Request, body: LoginRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> LoginResponse:
    cmd = LoginCmd(email=body.email, password=body.password)
    try:
        result = await svc.login(tenant_id, cmd)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AccountLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    if result.mfa_required:
        return LoginResponse(mfa_required=True, mfa_token=result.mfa_token)
    assert result.pair is not None
    return LoginResponse(
        access_token=result.pair.access_token,
        refresh_token=result.pair.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> TokenPairResponse:
    try:
        pair = await svc.refresh(tenant_id, body.refresh_token)
    except RefreshTokenInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return _pair_response(pair)


@router.post("/logout", status_code=204)
async def logout(
    body: RevokeRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> None:
    await svc.logout(tenant_id, body.refresh_token)


@router.post("/revoke", status_code=204)
async def revoke(
    body: RevokeRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> None:
    """OAuth2-revocation-flavored alias for /logout — same operation, kept
    as a separate route because this service's original design doc lists
    both verbs."""
    await svc.logout(tenant_id, body.refresh_token)


@router.post("/logout-all", status_code=204)
async def logout_all(subject: CurrentSubjectDep, svc: AuthServiceDep) -> None:
    await svc.logout_all(subject["tenant_id"], subject["user_id"])


@router.post("/introspect", response_model=IntrospectResponse)
async def introspect(body: IntrospectRequest) -> IntrospectResponse:
    """Always 200, per RFC 7662 — an invalid/expired token is a normal,
    successful introspection result (`active: false`), not an error."""
    try:
        claims = decode_access_token(body.token)
    except AccessTokenInvalidError:
        return IntrospectResponse(active=False)
    return IntrospectResponse(
        active=True,
        tenant_id=claims["tenant_id"],
        user_id=claims["user_id"],
        scopes=claims["scopes"],
    )


@router.post("/password/change", status_code=204)
async def change_password(
    body: ChangePasswordRequest, subject: CurrentSubjectDep, svc: AuthServiceDep
) -> None:
    cmd = ChangePasswordCmd(
        old_password=body.old_password, new_password=body.new_password
    )
    try:
        await svc.change_password(subject["tenant_id"], subject["user_id"], cmd)
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/password/forgot", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> ForgotPasswordResponse:
    raw_token = await svc.request_password_reset(tenant_id, body.email)
    if settings.environment == "production":
        return ForgotPasswordResponse()
    return ForgotPasswordResponse(reset_token=raw_token)


@router.post("/password/reset", status_code=204)
async def reset_password(
    body: ResetPasswordRequest, tenant_id: TenantIdDep, svc: AuthServiceDep
) -> None:
    cmd = ResetPasswordCmd(token=body.token, new_password=body.new_password)
    try:
        await svc.reset_password(tenant_id, cmd)
    except PasswordResetTokenInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    subject: CurrentSubjectDep, svc: AuthServiceDep
) -> SessionListResponse:
    sessions = await svc.list_sessions(subject["tenant_id"], subject["user_id"])
    return SessionListResponse(
        items=[SessionResponse.model_validate(s) for s in sessions]
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: UUID, subject: CurrentSubjectDep, svc: AuthServiceDep
) -> None:
    await svc.revoke_session(subject["tenant_id"], subject["user_id"], session_id)


@router.get("/events", response_model=AuthEventListResponse)
async def list_events(
    subject: CurrentSubjectDep,
    svc: AuthServiceDep,
    cursor: str | None = None,
    limit: int = 20,
) -> AuthEventListResponse:
    page = await svc.list_events(
        subject["tenant_id"], subject["user_id"], cursor=cursor, limit=limit
    )
    return AuthEventListResponse(
        items=[AuthEventResponse.model_validate(e) for e in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


# ---------------------------------------------------------------------------
# MFA (TOTP)
#
# Enrollment is two-phase: /mfa/setup returns the secret + recovery codes,
# then /mfa/activate confirms possession before MFA is enforced. /mfa/activate
# is added beyond the original 3-endpoint design doc (setup/verify/disable) for
# the same reason /auth/events was — a proper confirm step needs its own route.
# /mfa/verify is the public login step-up: it is the only MFA route reachable
# without a Bearer token, authenticated instead by the single-use mfa_token.
# ---------------------------------------------------------------------------


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(subject: CurrentSubjectDep, mfa: MfaServiceDep) -> MfaSetupResponse:
    try:
        enrollment = await mfa.setup(
            subject["tenant_id"], subject["user_id"], str(subject["user_id"])
        )
    except MfaAlreadyEnabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MfaSetupResponse(
        secret=enrollment.secret,
        otpauth_uri=enrollment.otpauth_uri,
        recovery_codes=enrollment.recovery_codes,
    )


@router.post("/mfa/activate", status_code=204)
async def mfa_activate(
    body: MfaActivateRequest, subject: CurrentSubjectDep, mfa: MfaServiceDep
) -> None:
    try:
        await mfa.activate(subject["tenant_id"], subject["user_id"], body.code)
    except MfaNotEnrolledError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MfaAlreadyEnabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidMfaCodeError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/mfa/verify", response_model=MfaVerifyResponse)
async def mfa_verify(
    body: MfaVerifyRequest, tenant_id: TenantIdDep, mfa: MfaServiceDep
) -> MfaVerifyResponse:
    """Public login step-up — authenticated by the single-use mfa_token from a
    login response, not a Bearer token."""
    try:
        pair = await mfa.verify_login(tenant_id, body.mfa_token, body.code)
    except InvalidMfaCodeError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return MfaVerifyResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/mfa/disable", status_code=204)
async def mfa_disable(
    body: MfaDisableRequest, subject: CurrentSubjectDep, mfa: MfaServiceDep
) -> None:
    try:
        await mfa.disable(subject["tenant_id"], subject["user_id"], body.code)
    except MfaNotEnrolledError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidMfaCodeError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
