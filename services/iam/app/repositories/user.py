from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

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

    async def list_users(
        self,
        *,
        q: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        is_verified: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        """Return a paginated, filtered slice of users and the total count."""
        base = select(User).options(*_EAGER)

        if q:
            from app.models.UserProfile.user_profile import UserProfile

            base = base.outerjoin(UserProfile, UserProfile.user_id == User.id).where(
                or_(
                    User.email.ilike(f"%{q}%"),
                    UserProfile.full_name.ilike(f"%{q}%"),
                )
            )
        if role is not None:
            base = (
                base.join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.slug == role)
            )
        if is_active is not None:
            base = base.where(User.is_active == is_active)
        if is_verified is not None:
            base = base.where(User.is_verified == is_verified)

        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        rows = (
            (await self.session.execute(base.offset(offset).limit(page_size)))
            .scalars()
            .all()
        )

        return list(rows), total

    async def save(self, user: User) -> User:
        """Commit an updated user instance and reload relationships."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        statement = select(User).where(User.id == user.id).options(*_EAGER)
        result = await self.session.execute(statement)
        return result.scalar_one()
