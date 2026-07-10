"""Profile/preferences/avatar/contact endpoints — mounted at
/api/v1/profiles/{user_id}.

Reads for a user_id with no local row yet return an empty/default-valued
response, not 404 — a user who exists but has never touched their profile
isn't an error. Writes 404 only if the user doesn't exist at all (checked
once, on first write — see ProfileService/AvatarService).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.v1.dependencies import AvatarServiceDep, ProfileServiceDep, TenantIdDep
from app.domain.commands import (
    SetAvatarCmd,
    UpdateContactCmd,
    UpdatePreferencesCmd,
    UpdateProfileCmd,
)
from app.domain.exceptions import UserNotFoundError
from app.schemas.avatar import AvatarResponse, SetAvatarRequest
from app.schemas.contact import ContactResponse, UpdateContactRequest
from app.schemas.preferences import PreferencesResponse, UpdatePreferencesRequest
from app.schemas.profile import ProfileResponse, UpdateProfileRequest

router = APIRouter(prefix="/profiles/{user_id}", tags=["Profiles"])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user_id: UUID, tenant_id: TenantIdDep, svc: ProfileServiceDep
) -> ProfileResponse:
    profile = await svc.get_profile(user_id, tenant_id)
    if profile is None:
        return ProfileResponse(user_id=user_id)
    return ProfileResponse.model_validate(profile)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    user_id: UUID,
    body: UpdateProfileRequest,
    tenant_id: TenantIdDep,
    svc: ProfileServiceDep,
) -> ProfileResponse:
    cmd = UpdateProfileCmd(
        bio=body.bio,
        pronouns=body.pronouns,
        display_name_override=body.display_name_override,
    )
    try:
        profile = await svc.update_profile(user_id, tenant_id, cmd)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProfileResponse.model_validate(profile)


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------


@router.post("/avatar", response_model=AvatarResponse)
async def set_avatar(
    user_id: UUID, body: SetAvatarRequest, tenant_id: TenantIdDep, svc: AvatarServiceDep
) -> AvatarResponse:
    cmd = SetAvatarCmd(url=body.url, content_type=body.content_type)
    try:
        avatar = await svc.set_avatar(user_id, tenant_id, cmd)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AvatarResponse.model_validate(avatar)


@router.delete("/avatar", status_code=204)
async def delete_avatar(
    user_id: UUID, tenant_id: TenantIdDep, svc: AvatarServiceDep
) -> None:
    await svc.delete_avatar(user_id, tenant_id)


@router.get("/avatar", response_model=AvatarResponse)
async def get_avatar(
    user_id: UUID, tenant_id: TenantIdDep, svc: AvatarServiceDep
) -> AvatarResponse:
    avatar = await svc.get_avatar(user_id, tenant_id)
    if avatar is None:
        return AvatarResponse(user_id=user_id)
    return AvatarResponse.model_validate(avatar)


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    user_id: UUID, tenant_id: TenantIdDep, svc: ProfileServiceDep
) -> PreferencesResponse:
    preferences = await svc.get_preferences(user_id, tenant_id)
    if preferences is None:
        return PreferencesResponse(user_id=user_id)
    return PreferencesResponse.model_validate(preferences)


@router.patch("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    user_id: UUID,
    body: UpdatePreferencesRequest,
    tenant_id: TenantIdDep,
    svc: ProfileServiceDep,
) -> PreferencesResponse:
    cmd = UpdatePreferencesCmd(
        locale=body.locale, timezone=body.timezone, extra=body.extra
    )
    try:
        preferences = await svc.update_preferences(user_id, tenant_id, cmd)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PreferencesResponse.model_validate(preferences)


# ---------------------------------------------------------------------------
# Contact info
# ---------------------------------------------------------------------------


@router.get("/contacts", response_model=ContactResponse)
async def get_contacts(
    user_id: UUID, tenant_id: TenantIdDep, svc: ProfileServiceDep
) -> ContactResponse:
    contact = await svc.get_contacts(user_id, tenant_id)
    if contact is None:
        return ContactResponse(user_id=user_id)
    return ContactResponse.model_validate(contact)


@router.patch("/contacts", response_model=ContactResponse)
async def update_contacts(
    user_id: UUID,
    body: UpdateContactRequest,
    tenant_id: TenantIdDep,
    svc: ProfileServiceDep,
) -> ContactResponse:
    cmd = UpdateContactCmd(
        phone=body.phone, secondary_email=body.secondary_email, address=body.address
    )
    try:
        contact = await svc.update_contacts(user_id, tenant_id, cmd)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ContactResponse.model_validate(contact)
