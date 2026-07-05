"""AccessReviewService — access-governance review lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateAccessReviewCmd, UpdateAccessReviewCmd
from app.domain.enums import AccessReviewStatus
from app.domain.exceptions import AccessReviewNotFoundError
from app.models.access_review import AccessReview
from app.repositories.access_review import AccessReviewFilter, AccessReviewRepository
from app.repositories.base import PageResult


class AccessReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AccessReviewRepository(session)

    async def create(self, cmd: CreateAccessReviewCmd) -> AccessReview:
        access_review = AccessReview(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            subject_user_id=cmd.subject_user_id,
            reviewer_id=cmd.reviewer_id,
            resource_type=cmd.resource_type,
            resource_id=cmd.resource_id,
            status=AccessReviewStatus.PENDING,
        )
        return await self._repo.create(access_review)

    async def get(
        self, access_review_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AccessReview:
        access_review = await self._repo.get_by_id(
            access_review_id, tenant_id=tenant_id
        )
        if access_review is None:
            raise AccessReviewNotFoundError(access_review_id)
        return access_review

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AccessReview]:
        filters = AccessReviewFilter(tenant_id=tenant_id)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def record_decision(
        self,
        access_review_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cmd: UpdateAccessReviewCmd,
    ) -> AccessReview:
        access_review = await self.get(access_review_id, tenant_id)

        access_review.status = cmd.status
        if cmd.decision_notes is not None:
            access_review.decision_notes = cmd.decision_notes
        if cmd.reviewer_id is not None:
            access_review.reviewer_id = cmd.reviewer_id
        access_review.reviewed_at = datetime.now(timezone.utc)

        return await self._repo.save(access_review)
