"""ProfileService — profile, preferences, and contact info.

Each resource is a 1-row-per-user singleton, created lazily on first
PATCH. UserProfileManagement's existence check used to be a fail-fast HTTP
call to a separate UserManagement service; now that both are the same
service and the same transaction, it's just a direct repository lookup —
no network round trip, no separate "unreachable" error class, and no risk
of the check and the write racing across two different databases.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import UpdateContactCmd, UpdatePreferencesCmd, UpdateProfileCmd
from app.domain.exceptions import UserNotFoundError
from app.models.contact_info import ContactInfo
from app.models.user_preferences import UserPreferences
from app.models.user_profile import UserProfile
from app.repositories.contact_info import ContactInfoRepository
from app.repositories.user import UserRepository
from app.repositories.user_preferences import UserPreferencesRepository
from app.repositories.user_profile import UserProfileRepository


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._profile_repo = UserProfileRepository(session)
        self._preferences_repo = UserPreferencesRepository(session)
        self._contact_repo = ContactInfoRepository(session)

    async def _assert_user_exists(self, user_id: UUID, tenant_id: UUID) -> None:
        user = await self._user_repo.get_by_id(user_id, tenant_id=tenant_id)
        if user is None:
            raise UserNotFoundError(user_id)

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    async def get_profile(self, user_id: UUID, tenant_id: UUID) -> UserProfile | None:
        return await self._profile_repo.get_by_user_id(user_id, tenant_id=tenant_id)

    async def update_profile(
        self, user_id: UUID, tenant_id: UUID, cmd: UpdateProfileCmd
    ) -> UserProfile:
        profile = await self._profile_repo.get_by_user_id(user_id, tenant_id=tenant_id)
        if profile is None:
            await self._assert_user_exists(user_id, tenant_id)
            profile = UserProfile(user_id=user_id, tenant_id=tenant_id)

        if cmd.bio is not None:
            profile.bio = cmd.bio
        if cmd.pronouns is not None:
            profile.pronouns = cmd.pronouns
        if cmd.display_name_override is not None:
            profile.display_name_override = cmd.display_name_override

        return await self._profile_repo.save(profile)

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    async def get_preferences(
        self, user_id: UUID, tenant_id: UUID
    ) -> UserPreferences | None:
        return await self._preferences_repo.get_by_user_id(user_id, tenant_id=tenant_id)

    async def update_preferences(
        self, user_id: UUID, tenant_id: UUID, cmd: UpdatePreferencesCmd
    ) -> UserPreferences:
        preferences = await self._preferences_repo.get_by_user_id(
            user_id, tenant_id=tenant_id
        )
        if preferences is None:
            await self._assert_user_exists(user_id, tenant_id)
            preferences = UserPreferences(user_id=user_id, tenant_id=tenant_id)

        if cmd.locale is not None:
            preferences.locale = cmd.locale
        if cmd.timezone is not None:
            preferences.timezone = cmd.timezone
        if cmd.extra is not None:
            preferences.extra = cmd.extra

        return await self._preferences_repo.save(preferences)

    # ------------------------------------------------------------------
    # Contact info
    # ------------------------------------------------------------------

    async def get_contacts(self, user_id: UUID, tenant_id: UUID) -> ContactInfo | None:
        return await self._contact_repo.get_by_user_id(user_id, tenant_id=tenant_id)

    async def update_contacts(
        self, user_id: UUID, tenant_id: UUID, cmd: UpdateContactCmd
    ) -> ContactInfo:
        contact = await self._contact_repo.get_by_user_id(user_id, tenant_id=tenant_id)
        if contact is None:
            await self._assert_user_exists(user_id, tenant_id)
            contact = ContactInfo(user_id=user_id, tenant_id=tenant_id)

        if cmd.phone is not None:
            contact.phone = cmd.phone
        if cmd.secondary_email is not None:
            contact.secondary_email = cmd.secondary_email
        if cmd.address is not None:
            contact.address = cmd.address

        return await self._contact_repo.save(contact)
