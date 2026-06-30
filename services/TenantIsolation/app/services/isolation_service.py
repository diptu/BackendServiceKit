"""IsolationService — core business logic for access validation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    CACHE_TTL_ALLOW_DECISION,
    CACHE_TTL_DENY_DECISION,
    CACHE_TTL_POLICY,
)
from app.domain.enums import AccessAction, IsolationDecision, PolicyType
from app.domain.events import IsolationViolationDetected, PolicyUpdated
from app.domain.exceptions import (
    ContextResolutionError,
    InvalidQueryFilterError,
    IsolationViolationError,
    IsolationValidationError,
)
from app.events.isolation_events import EventPublisher, publish_event
from app.infrastructure.cache.redis_cache import (
    cache_delete,
    cache_delete_by_prefix,
    cache_get,
    cache_get_str,
    cache_set,
    cache_set_str,
    claim_cache_key,
    decision_cache_key,
    policy_cache_key,
)
from app.infrastructure.messaging.publisher import NullPublisher
from app.models.access_decision_log import AccessDecisionLog
from app.models.isolation_policy import IsolationPolicy
from app.repositories.access_decision_log import AccessDecisionLogRepository
from app.repositories.base import PageResult
from app.repositories.isolation_policy import IsolationPolicyRepository
from app.repositories.resource_claim import ResourceClaimRepository
from app.schemas.isolation import (
    CheckAccessResponse,
    PolicyUpdateRequest,
    ResolveContextResponse,
    ValidateQueryResponse,
    ValidateResourceResponse,
    ValidateResponse,
)
from app.validators.isolation_validator import (
    validate_policy_update,
    validate_query_filter,
    validate_resource_ids,
)

logger = logging.getLogger(__name__)


class IsolationService:
    __slots__ = ("_policy_repo", "_claim_repo", "_log_repo", "_publisher")

    def __init__(self, session: AsyncSession, publisher: Any = None) -> None:
        self._policy_repo = IsolationPolicyRepository(session)
        self._claim_repo = ResourceClaimRepository(session)
        self._log_repo = AccessDecisionLogRepository(session)
        self._publisher: EventPublisher = publisher or NullPublisher()

    async def validate(
        self,
        caller_tenant_id: UUID,
        resource_ids: list[str],
        resource_type: str,
    ) -> ValidateResponse:
        validate_resource_ids(resource_ids)

        violations: list[str] = []
        for resource_id in resource_ids:
            ckey = claim_cache_key(resource_type, resource_id)
            cached_owner = await cache_get_str(ckey)
            if cached_owner is not None:
                if cached_owner != str(caller_tenant_id):
                    violations.append(resource_id)
                continue

            claim = await self._claim_repo.get_owner(resource_id, resource_type)
            if claim is None:
                violations.append(resource_id)
                continue

            await cache_set_str(ckey, str(claim.tenant_id), ttl=CACHE_TTL_POLICY)

            if claim.tenant_id != caller_tenant_id:
                violations.append(resource_id)

        decision = IsolationDecision.DENY if violations else IsolationDecision.ALLOW
        return ValidateResponse(
            decision=decision,
            violations=violations,
            caller_tenant_id=caller_tenant_id,
            resource_type=resource_type,
        )

    async def check_access(
        self,
        caller_tenant_id: UUID,
        target_tenant_id: UUID,
        resource_id: str,
        resource_type: str,
        action: str,
        *,
        request_id: str | None = None,
    ) -> CheckAccessResponse:
        dkey = decision_cache_key(
            str(caller_tenant_id), str(target_tenant_id), resource_id, resource_type, action
        )
        cached = await cache_get(dkey)
        if cached is not None:
            return CheckAccessResponse(**cached)

        if caller_tenant_id == target_tenant_id:
            decision = IsolationDecision.ALLOW
            reason = "same-tenant access always allowed"
        else:
            policy = await self._policy_repo.get_active_by_tenant(caller_tenant_id)
            policy_type = PolicyType(policy.policy_type) if policy else PolicyType.STRICT

            if policy_type == PolicyType.INTERNAL:
                decision = IsolationDecision.ALLOW
                reason = "internal policy bypasses isolation"
            elif policy_type == PolicyType.PARTNER:
                allowed_ids = policy.allowed_partner_tenant_ids if policy else []
                if str(target_tenant_id) in [str(x) for x in allowed_ids]:
                    if action == AccessAction.READ:
                        decision = IsolationDecision.ALLOW
                        reason = "partner cross-tenant read allowed"
                    else:
                        decision = IsolationDecision.DENY
                        reason = f"partner policy allows read only, not '{action}'"
                else:
                    decision = IsolationDecision.DENY
                    reason = "target tenant not in allowed partner list"
            else:
                decision = IsolationDecision.DENY
                reason = "strict isolation policy denies cross-tenant access"

        log = AccessDecisionLog(
            id=uuid4(),
            caller_tenant_id=caller_tenant_id,
            target_tenant_id=target_tenant_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            decision=decision.value,
            reason=reason,
            request_id=request_id,
            decided_at=datetime.now(timezone.utc),
        )
        await self._log_repo.create(log)

        resp = CheckAccessResponse(
            decision=decision,
            reason=reason,
            caller_tenant_id=caller_tenant_id,
            target_tenant_id=target_tenant_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
        )

        ttl = CACHE_TTL_ALLOW_DECISION if decision == IsolationDecision.ALLOW else CACHE_TTL_DENY_DECISION
        await cache_set(dkey, resp.model_dump(mode="json"), ttl=ttl)

        if decision == IsolationDecision.DENY:
            await publish_event(
                IsolationViolationDetected(
                    caller_tenant_id=caller_tenant_id,
                    target_tenant_id=target_tenant_id,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    action=action,
                ),
                self._publisher,
            )

        return resp

    async def resolve_context(self, token: str) -> ResolveContextResponse:
        try:
            from jose import JWTError, jwt  # type: ignore[import-untyped]

            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.jwt_algorithm]
            )
            tenant_id = UUID(str(payload["tenant_id"]))
            user_id_raw = payload.get("user_id") or payload.get("sub")
            user_id: UUID | None = None
            if user_id_raw:
                try:
                    user_id = UUID(str(user_id_raw))
                except (ValueError, AttributeError):
                    user_id = None

            return ResolveContextResponse(
                tenant_id=tenant_id,
                user_id=user_id,
                token_type="bearer",
            )
        except (KeyError, ValueError) as exc:
            raise ContextResolutionError(
                f"Cannot resolve tenant context from token: {exc}"
            ) from exc
        except Exception as exc:
            raise ContextResolutionError(
                f"Cannot resolve tenant context from token: {exc}"
            ) from exc

    async def validate_resource(
        self,
        caller_tenant_id: UUID,
        resource_id: str,
        resource_type: str,
    ) -> ValidateResourceResponse:
        ckey = claim_cache_key(resource_type, resource_id)
        cached_owner = await cache_get_str(ckey)

        if cached_owner is not None:
            owner_id = UUID(cached_owner)
            decision = (
                IsolationDecision.ALLOW if owner_id == caller_tenant_id else IsolationDecision.DENY
            )
            return ValidateResourceResponse(
                decision=decision,
                owner_tenant_id=owner_id,
            )

        claim = await self._claim_repo.get_owner(resource_id, resource_type)
        if claim is None:
            return ValidateResourceResponse(
                decision=IsolationDecision.DENY,
                owner_tenant_id=None,
            )

        await cache_set_str(ckey, str(claim.tenant_id), ttl=CACHE_TTL_POLICY)

        decision = (
            IsolationDecision.ALLOW
            if claim.tenant_id == caller_tenant_id
            else IsolationDecision.DENY
        )
        return ValidateResourceResponse(
            decision=decision,
            owner_tenant_id=claim.tenant_id,
        )

    async def validate_query(
        self,
        caller_tenant_id: UUID,
        query_filter: dict[str, str],
    ) -> ValidateQueryResponse:
        validate_query_filter(query_filter)

        filter_tenant_id_str = query_filter["tenant_id"]
        try:
            filter_tenant_id = UUID(filter_tenant_id_str)
        except (ValueError, AttributeError) as exc:
            raise IsolationValidationError(
                f"query_filter.tenant_id is not a valid UUID: '{filter_tenant_id_str}'."
            ) from exc

        if filter_tenant_id != caller_tenant_id:
            raise IsolationViolationError(
                f"query_filter.tenant_id '{filter_tenant_id}' does not match "
                f"caller tenant '{caller_tenant_id}'."
            )

        return ValidateQueryResponse(is_valid=True, reason=None)

    async def list_policies(
        self,
        tenant_id: UUID,
        *,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[IsolationPolicy]:
        return await self._policy_repo.list_by_tenant(
            tenant_id, next_cursor=next_cursor, limit=limit
        )

    async def update_policy(
        self, policy_id: UUID, updates: PolicyUpdateRequest
    ) -> IsolationPolicy:
        validate_policy_update(updates.allowed_partner_tenant_ids)

        kwargs: dict[str, object] = {}
        if updates.name is not None:
            kwargs["name"] = updates.name
        if updates.policy_type is not None:
            kwargs["policy_type"] = updates.policy_type
        if updates.allow_cross_tenant_read is not None:
            kwargs["allow_cross_tenant_read"] = updates.allow_cross_tenant_read
        if updates.allowed_partner_tenant_ids is not None:
            kwargs["allowed_partner_tenant_ids"] = updates.allowed_partner_tenant_ids
        if updates.is_active is not None:
            kwargs["is_active"] = updates.is_active

        policy = await self._policy_repo.update(policy_id, **kwargs)

        await cache_delete(policy_cache_key(str(policy.tenant_id)))
        # Invalidate all decision-cache entries where this tenant was the caller;
        # without this, cached ALLOW decisions from the old policy survive the TTL.
        await cache_delete_by_prefix(f"isolation:decision:{policy.tenant_id}:")

        await publish_event(
            PolicyUpdated(
                tenant_id=policy.tenant_id,
                policy_id=policy_id,
                changes=dict(kwargs),
            ),
            self._publisher,
        )

        return policy
