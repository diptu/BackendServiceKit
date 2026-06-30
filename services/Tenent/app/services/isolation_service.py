"""IsolationService — tenant boundary enforcement + Redis decision cache."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import isolation_decisions_total, isolation_violations_total
from app.domain.enums import (
    AccessAction,
    IsolationDecision,
    PolicyType,
    ResourceType,
)
from app.domain.exceptions import (
    ContextResolutionError,
    InvalidQueryFilterError,
    IsolationViolationError,
    PolicyNotFoundError,
    ResourceClaimNotFoundError,
)
from app.infrastructure.cache.redis_cache import (
    cache_delete,
    cache_get_str,
    cache_set_str,
    decision_cache_key,
    policy_cache_key,
)
from app.models.access_decision_log import AccessDecisionLog
from app.models.isolation_policy import IsolationPolicy
from app.repositories.access_decision_log import AccessDecisionLogRepository
from app.repositories.isolation_policy import IsolationPolicyRepository
from app.repositories.resource_claim import ResourceClaimRepository

logger = logging.getLogger(__name__)

_DECISION_TTL = 300  # seconds
_POLICY_TTL = 600


class IsolationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policy_repo = IsolationPolicyRepository(session)
        self._claim_repo = ResourceClaimRepository(session)
        self._log_repo = AccessDecisionLogRepository(session)

    # ------------------------------------------------------------------
    # Core: validate cross-tenant access
    # ------------------------------------------------------------------

    async def validate(
        self,
        caller_tenant_id: uuid.UUID,
        target_tenant_id: uuid.UUID,
        resource_id: str | None = None,
        resource_type: str | None = None,
    ) -> tuple[bool, IsolationDecision, str | None]:
        if caller_tenant_id == target_tenant_id:
            return True, IsolationDecision.ALLOW, "same_tenant"

        policy = await self._load_policy(caller_tenant_id)

        if policy is None or policy.policy_type == PolicyType.STRICT:
            reason = "strict_isolation_no_cross_tenant"
            isolation_violations_total.inc()
            return False, IsolationDecision.DENY, reason

        if policy.policy_type == PolicyType.INTERNAL:
            return True, IsolationDecision.ALLOW, "internal_policy_allows_cross_tenant"

        # PARTNER — check if target is in allowed list
        allowed: list[str] = [str(t) for t in (policy.allowed_partner_tenant_ids or [])]
        if str(target_tenant_id) in allowed:
            return True, IsolationDecision.ALLOW, "partner_allowed"

        isolation_violations_total.inc()
        return False, IsolationDecision.DENY, "partner_not_in_allowed_list"

    # ------------------------------------------------------------------
    # check_access — with Redis cache + audit log
    # ------------------------------------------------------------------

    async def check_access(
        self,
        caller_tenant_id: uuid.UUID,
        target_tenant_id: uuid.UUID,
        resource_id: str,
        resource_type: ResourceType,
        action: AccessAction,
        *,
        request_id: str | None = None,
    ) -> tuple[bool, IsolationDecision, str | None, bool]:
        cache_key = decision_cache_key(
            str(caller_tenant_id),
            str(target_tenant_id),
            str(resource_type),
            resource_id,
            str(action),
        )
        cached = await cache_get_str(cache_key)
        if cached is not None:
            data = json.loads(cached)
            decision = IsolationDecision(data["decision"])
            isolation_decisions_total.labels(decision=decision.value).inc()
            return data["allowed"], decision, data.get("reason"), True

        allowed, decision, reason = await self.validate(
            caller_tenant_id, target_tenant_id
        )

        isolation_decisions_total.labels(decision=decision.value).inc()

        await cache_set_str(
            cache_key,
            json.dumps(
                {"allowed": allowed, "decision": decision.value, "reason": reason}
            ),
            ttl=_DECISION_TTL,
        )

        await self._log_decision(
            caller_tenant_id=caller_tenant_id,
            target_tenant_id=target_tenant_id,
            resource_id=resource_id,
            resource_type=str(resource_type),
            action=str(action),
            decision=decision,
            reason=reason,
            request_id=request_id,
        )

        if not allowed:
            raise IsolationViolationError(reason or "access_denied")

        return allowed, decision, reason, False

    # ------------------------------------------------------------------
    # resolve_context — extract tenant identity from JWT
    # ------------------------------------------------------------------

    async def resolve_context(self, token: str) -> dict[str, object]:
        try:
            from jose import jwt as _jwt  # type: ignore[import-untyped]

            payload: dict[str, object] = _jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            tenant_id_raw = payload.get("tenant_id")
            if tenant_id_raw is None:
                raise ContextResolutionError("JWT missing tenant_id claim.")

            return {
                "tenant_id": uuid.UUID(str(tenant_id_raw)),
                "user_id": (
                    uuid.UUID(str(payload["user_id"])) if "user_id" in payload else None
                ),
                "scopes": payload.get("scopes", []),
            }
        except ContextResolutionError:
            raise
        except Exception as exc:
            raise ContextResolutionError(str(exc)) from exc

    # ------------------------------------------------------------------
    # validate_resource — check resource ownership
    # ------------------------------------------------------------------

    async def validate_resource(
        self,
        caller_tenant_id: uuid.UUID,
        resource_id: str,
        resource_type: ResourceType,
    ) -> tuple[bool, str | None, uuid.UUID | None]:
        claim = await self._claim_repo.get_owner(resource_id, str(resource_type))
        if claim is None:
            raise ResourceClaimNotFoundError(resource_id, str(resource_type))

        if claim.tenant_id == caller_tenant_id:
            return True, None, claim.tenant_id

        return False, "resource_owned_by_different_tenant", claim.tenant_id

    # ------------------------------------------------------------------
    # validate_query — check query filters for tenant scoping
    # ------------------------------------------------------------------

    async def validate_query(
        self,
        caller_tenant_id: uuid.UUID,
        filters: dict[str, object],
    ) -> tuple[bool, str | None]:
        tid_in_filter = filters.get("tenant_id")
        if tid_in_filter is None:
            raise InvalidQueryFilterError("Query must include tenant_id filter.")
        if str(tid_in_filter) != str(caller_tenant_id):
            raise InvalidQueryFilterError(
                f"Query tenant_id {tid_in_filter!r} does not match caller {caller_tenant_id}."
            )
        return True, None

    # ------------------------------------------------------------------
    # Policy CRUD
    # ------------------------------------------------------------------

    async def list_policies(
        self, tenant_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> object:
        return await self._policy_repo.list_by_tenant(
            tenant_id, next_cursor=cursor, limit=limit
        )

    async def create_policy(
        self,
        tenant_id: uuid.UUID,
        name: str,
        policy_type: PolicyType = PolicyType.STRICT,
        allow_cross_tenant_read: bool = False,
        allowed_partner_tenant_ids: list[uuid.UUID] | None = None,
    ) -> IsolationPolicy:
        policy = IsolationPolicy(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            policy_type=str(policy_type),
            allow_cross_tenant_read=allow_cross_tenant_read,
            allowed_partner_tenant_ids=[
                str(tid) for tid in (allowed_partner_tenant_ids or [])
            ],
        )
        result = await self._policy_repo.create(policy)
        await cache_delete(policy_cache_key(str(tenant_id)))
        return result

    async def get_policy(self, policy_id: uuid.UUID) -> IsolationPolicy:
        policy = await self._policy_repo.get_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy

    async def update_policy(
        self, policy_id: uuid.UUID, updates: dict[str, object]
    ) -> IsolationPolicy:
        policy = await self.get_policy(policy_id)
        result = await self._policy_repo.update(policy_id, **updates)
        await cache_delete(policy_cache_key(str(policy.tenant_id)))
        return result

    # ------------------------------------------------------------------
    # Audit logs
    # ------------------------------------------------------------------

    async def list_decisions(
        self, tenant_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> object:
        return await self._log_repo.list_by_tenant(
            tenant_id, next_cursor=cursor, limit=limit
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_policy(self, tenant_id: uuid.UUID) -> IsolationPolicy | None:
        cached_str = await cache_get_str(policy_cache_key(str(tenant_id)))
        if cached_str is not None:
            return None  # if cached as None sentinel
        return await self._policy_repo.get_active_by_tenant(tenant_id)

    async def _log_decision(
        self,
        *,
        caller_tenant_id: uuid.UUID,
        target_tenant_id: uuid.UUID,
        resource_id: str,
        resource_type: str,
        action: str,
        decision: IsolationDecision,
        reason: str | None,
        request_id: str | None,
    ) -> None:
        log = AccessDecisionLog(
            id=uuid.uuid4(),
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
        try:
            await self._log_repo.create(log)
        except Exception:
            logger.warning("access_decision_log_failed", exc_info=True)
