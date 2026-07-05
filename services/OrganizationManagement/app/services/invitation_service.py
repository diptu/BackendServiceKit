"""InvitationService — secure, single-use organization invitations.

Only a SHA-256 hash of the raw token is ever persisted; the raw token is
returned once, in the create-invitation response, and never stored or
logged. Accepting an invitation atomically flips its status to accepted
(within the same DB transaction as the membership insert), which is what
prevents replay — a second accept attempt with the same token fails the
status check even though the hash still matches.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import AcceptInvitationCmd, AddMemberCmd, CreateInvitationCmd
from app.domain.enums import InvitationStatus
from app.domain.events import InvitationAccepted, InvitationCreated, InvitationRevoked
from app.domain.exceptions import InvitationInvalidError, InvitationNotFoundError
from app.models.organization_invitation import OrganizationInvitation
from app.models.organization_membership import OrganizationMembership
from app.repositories.base import PageResult
from app.repositories.organization_event import OrganizationEventRepository
from app.repositories.organization_invitation import OrganizationInvitationRepository
from app.services.membership_service import MembershipService


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on DateTime(timezone=True) columns (Postgres
    doesn't) — treat a naive value read back from the DB as UTC rather than
    failing the comparison below."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class InvitationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OrganizationInvitationRepository(session)
        self._events_repo = OrganizationEventRepository(session)
        self._membership_svc = MembershipService(session)

    async def create_invitation(
        self, organization_id: uuid.UUID, tenant_id: uuid.UUID, cmd: CreateInvitationCmd
    ) -> tuple[OrganizationInvitation, str]:
        raw_token = secrets.token_urlsafe(32)
        invitation = OrganizationInvitation(
            id=uuid.uuid4(),
            organization_id=organization_id,
            tenant_id=tenant_id,
            email=cmd.email,
            token_hash=_hash_token(raw_token),
            role=cmd.role,
            status=InvitationStatus.PENDING,
            invited_by=cmd.invited_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=cmd.expires_in_days),
        )
        await self._repo.create(invitation)

        await self._events_repo.record(
            organization_id,
            tenant_id,
            InvitationCreated(
                organization_id=organization_id,
                invitation_id=invitation.id,
                email=cmd.email,
                role=cmd.role,
                invited_by=cmd.invited_by,
            ),
            performed_by=cmd.invited_by,
        )
        return invitation, raw_token

    async def accept_invitation(
        self, cmd: AcceptInvitationCmd
    ) -> OrganizationMembership:
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

        membership = await self._membership_svc.add_member(
            invitation.organization_id,
            invitation.tenant_id,
            AddMemberCmd(
                user_id=cmd.user_id,
                role=invitation.role,
                added_by=invitation.invited_by,
            ),
        )

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        await self._repo.save(invitation)

        await self._events_repo.record(
            invitation.organization_id,
            invitation.tenant_id,
            InvitationAccepted(
                invitation_id=invitation.id,
                organization_id=invitation.organization_id,
                user_id=cmd.user_id,
            ),
            performed_by=cmd.user_id,
        )
        return membership

    async def revoke_invitation(
        self,
        organization_id: uuid.UUID,
        tenant_id: uuid.UUID,
        invitation_id: uuid.UUID,
        *,
        revoked_by: uuid.UUID | None = None,
    ) -> OrganizationInvitation:
        invitation = await self._repo.get_by_id(
            invitation_id, organization_id=organization_id
        )
        if invitation is None:
            raise InvitationNotFoundError(invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationInvalidError(
                f"invitation is {invitation.status}, not pending"
            )

        invitation.status = InvitationStatus.REVOKED
        invitation.revoked_at = datetime.now(timezone.utc)
        saved = await self._repo.save(invitation)

        await self._events_repo.record(
            organization_id,
            tenant_id,
            InvitationRevoked(
                invitation_id=invitation_id,
                organization_id=organization_id,
                revoked_by=revoked_by,
            ),
            performed_by=revoked_by,
        )
        return saved

    async def list_invitations(
        self, organization_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> PageResult[OrganizationInvitation]:
        return await self._repo.list_for_organization(
            organization_id, cursor=cursor, limit=limit
        )
