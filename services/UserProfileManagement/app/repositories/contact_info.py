"""Repository for ContactInfo."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.contact_info import ContactInfo
from app.repositories.base import BaseRepository


class ContactInfoRepository(BaseRepository[ContactInfo]):
    async def get_by_user_id(self, user_id: UUID) -> ContactInfo | None:
        result = await self._session.execute(
            select(ContactInfo).where(ContactInfo.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def save(self, contact: ContactInfo) -> ContactInfo:
        self._session.add(contact)
        await self._session.flush()
        await self._session.refresh(contact)
        return contact
