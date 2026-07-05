"""InvitationService — secure, single-use platform onboarding invitations.

Only a SHA-256 hash of the raw token is ever persisted; the raw token is
returned once, in the create-invitation response, and never stored or
logged. Accepting an invitation atomically flips its status to accepted
(within the same DB transaction as the User row insert), which is what
prevents replay. Pattern (including the SQLite/Postgres timezone-comparison
fix) copied from OrganizationManagement's InvitationService — see this
service's TODO.md for why that bug happens and how it's avoided here.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import AcceptInvitationCmd, CreateInvitationCmd, CreateUserCmd
from app.domain.enums import InvitationStatus
from app.domain.events import InvitationAccepted, InvitationCreated, InvitationRevoked
from app.domain.exceptions import InvitationInvalidError, InvitationNotFoundError
from app.infrastructure.messaging.publisher import NullPublisher, RabbitMQPublisher
from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.repositories.base import PageResult
from app.repositories.user_invitation import UserInvitationRepository
from app.services.user_service import UserService


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on DateTime(timezone=True) columns (Postgres
    doesn't) — treat a naive value read back from the DB as UTC rather than
    failing the comparison below."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class InvitationService:
    def __init__(
        self,
        session: AsyncSession,
        publisher: RabbitMQPublisher | NullPublisher | None = None,
    ) -> None:
        self._session = session
        self._repo = UserInvitationRepository(session)
        self._publisher = publisher or NullPublisher()
        self._user_svc = UserService(session, publisher)

    async def create_invitation(
        self, tenant_id: uuid.UUID, cmd: CreateInvitationCmd
    ) -> tuple[UserInvitation, str]:
        raw_token = secrets.token_urlsafe(32)
        invitation = UserInvitation(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=cmd.email,
            token_hash=_hash_token(raw_token),
            status=InvitationStatus.PENDING,
            invited_by=cmd.invited_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=cmd.expires_in_days),
        )
        await self._repo.create(invitation)

        await self._publisher.publish(
            "invitation.created",
            InvitationCreated(
                invitation_id=invitation.id,
                tenant_id=tenant_id,
                email=cmd.email,
                invited_by=cmd.invited_by,
            ),
        )
        return invitation, raw_token

    async def accept_invitation(self, cmd: AcceptInvitationCmd) -> User:
        invitation = await self._repo.get_by_token_hash(_hash_token(cmd.token))
        if invitation is None:
            raise InvitationInvalidError("unknown token")
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationInvalidError(
                f"invitation is {invitation.status}, not pending"
            )
        if _as_aware_utc(invitation.expires_at) < datetime.now(timezone.utc):
            invitation.status = InvitationStatus.EXPIRED
            await self._repo.save(invitation)
            raise InvitationInvalidError("invitation has expired")

        user = await self._user_svc.create(
            CreateUserCmd(
                tenant_id=invitation.tenant_id,
                email=invitation.email,
                first_name=cmd.first_name,
                last_name=cmd.last_name,
            )
        )

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        await self._repo.save(invitation)

        await self._publisher.publish(
            "invitation.accepted",
            InvitationAccepted(
                invitation_id=invitation.id,
                tenant_id=invitation.tenant_id,
                user_id=user.id,
            ),
        )
        return user

    async def revoke_invitation(
        self,
        tenant_id: uuid.UUID,
        invitation_id: uuid.UUID,
        *,
        revoked_by: uuid.UUID | None = None,
    ) -> UserInvitation:
        invitation = await self._repo.get_by_id(invitation_id, tenant_id=tenant_id)
        if invitation is None:
            raise InvitationNotFoundError(invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationInvalidError(
                f"invitation is {invitation.status}, not pending"
            )

        invitation.status = InvitationStatus.REVOKED
        invitation.revoked_at = datetime.now(timezone.utc)
        saved = await self._repo.save(invitation)

        await self._publisher.publish(
            "invitation.revoked",
            InvitationRevoked(
                invitation_id=invitation_id, tenant_id=tenant_id, revoked_by=revoked_by
            ),
        )
        return saved

    async def list_invitations(
        self, tenant_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> PageResult[UserInvitation]:
        return await self._repo.list_for_tenant(tenant_id, cursor=cursor, limit=limit)
