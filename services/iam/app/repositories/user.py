from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User

_EAGER = (selectinload(User.profile), selectinload(User.roles))


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        """Persist a new user instance and eagerly load relationships."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        statement = select(User).where(User.id == user.id).options(*_EAGER)
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user record by their unique email address."""
        statement = select(User).where(User.email == email).options(*_EAGER)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user record by their unique database primary key ID."""
        statement = select(User).where(User.id == user_id).options(*_EAGER)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_oauth_id(self, provider: str, oauth_id: str) -> User | None:
        """Fetch a user by their federated identity (provider + provider sub)."""
        statement = (
            select(User)
            .where(User.oauth_provider == provider, User.oauth_id == oauth_id)
            .options(*_EAGER)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def set_oauth(self, user_id: UUID, provider: str, oauth_id: str) -> User:
        """
        Link an OAuth identity to an existing local user.

        Safe to call when the user previously had no OAuth link; raises
        IntegrityError at the DB level if the (provider, oauth_id) pair is
        already owned by a different user.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            msg = f"User {user_id} not found"
            raise ValueError(msg)
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        return await self.save(user)

    async def update_last_login(self, user: User) -> User:
        """Update last_login_at and persist."""
        now = datetime.now(UTC)
        user.last_login_at = now
        user.updated_at = now
        return await self.save(user)

    async def save(self, user: User) -> User:
        """Commit an updated user instance and reload relationships."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        statement = select(User).where(User.id == user.id).options(*_EAGER)
        result = await self.session.execute(statement)
        return result.scalar_one()
