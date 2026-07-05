"""ProfileService — profile, preferences, and contact info.

Each resource is a 1-row-per-user singleton, created lazily on first
PATCH. The fail-fast existence check against UserManagement fires once
per resource type (not once per user across all four tables — see
TODO.md's "Second pass" for why that's a deliberate simplification from
the original plan), and only when no local row exists yet for that
resource — subsequent calls trust the local row's mere existence as proof
the user was already validated.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import UpdateContactCmd, UpdatePreferencesCmd, UpdateProfileCmd
from app.infrastructure.clients.user_profile_client import UserProfileClient
from app.models.contact_info import ContactInfo
from app.models.user_preferences import UserPreferences
from app.models.user_profile import UserProfile
from app.repositories.contact_info import ContactInfoRepository
from app.repositories.user_preferences import UserPreferencesRepository
from app.repositories.user_profile import UserProfileRepository


class ProfileService:
    def __init__(
        self,
        session: AsyncSession,
        client: UserProfileClient | None = None,
    ) -> None:
        self._session = session
        self._profile_repo = UserProfileRepository(session)
        self._preferences_repo = UserPreferencesRepository(session)
        self._contact_repo = ContactInfoRepository(session)
        self._client = client or UserProfileClient()

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        return await self._profile_repo.get_by_user_id(user_id)

    async def update_profile(
        self, user_id: UUID, tenant_id: UUID, cmd: UpdateProfileCmd
    ) -> UserProfile:
        profile = await self._profile_repo.get_by_user_id(user_id)
        if profile is None:
            await self._client.assert_user_exists(user_id, tenant_id)
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

    async def get_preferences(self, user_id: UUID) -> UserPreferences | None:
        return await self._preferences_repo.get_by_user_id(user_id)

    async def update_preferences(
        self, user_id: UUID, tenant_id: UUID, cmd: UpdatePreferencesCmd
    ) -> UserPreferences:
        preferences = await self._preferences_repo.get_by_user_id(user_id)
        if preferences is None:
            await self._client.assert_user_exists(user_id, tenant_id)
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

    async def get_contacts(self, user_id: UUID) -> ContactInfo | None:
        return await self._contact_repo.get_by_user_id(user_id)

    async def update_contacts(
        self, user_id: UUID, tenant_id: UUID, cmd: UpdateContactCmd
    ) -> ContactInfo:
        contact = await self._contact_repo.get_by_user_id(user_id)
        if contact is None:
            await self._client.assert_user_exists(user_id, tenant_id)
            contact = ContactInfo(user_id=user_id, tenant_id=tenant_id)

        if cmd.phone is not None:
            contact.phone = cmd.phone
        if cmd.secondary_email is not None:
            contact.secondary_email = cmd.secondary_email
        if cmd.address is not None:
            contact.address = cmd.address

        return await self._contact_repo.save(contact)
