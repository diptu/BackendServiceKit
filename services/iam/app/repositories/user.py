from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        """Persist a new user instance and eagerly load relationships."""
        self.session.add(user)
        await self.session.commit()

        # 1. Refresh primary scalar attributes (like generated UUIDs, timestamps)
        await self.session.refresh(user)

        # 2. Re-select with selectinload to populate relationships safely for async context
        statement = (
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.profile), selectinload(User.roles))
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user record by their unique email address."""
        statement = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.profile), selectinload(User.roles))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user record by their unique database primary key ID."""
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.profile), selectinload(User.roles))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_last_login(self, user: User) -> User:
        """
        Updates the last login tracking metrics on the user model instance
        and saves it safely, eagerly reloading relationships to prevent lazy-load errors.
        """
        now = datetime.now(UTC)
        user.last_login_at = now
        user.updated_at = (
            now  # Pre-emptively sync memory state for instant availability
        )

        # Leverage your existing save method which executes selectinload
        return await self.save(user)

    async def save(self, user: User) -> User:
        """Commit an updated user instance and reload relationships."""
        self.session.add(user)
        await self.session.commit()

        # 1. Refresh scalar updates (like automatic updated_at values)
        await self.session.refresh(user)

        # 2. Re-select with selectinload to guarantee relationships are unexpired and loaded
        statement = (
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.profile), selectinload(User.roles))
        )
        result = await self.session.execute(statement)
        return result.scalar_one()
