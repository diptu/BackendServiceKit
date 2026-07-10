"""PolicyEvaluationService — the ABAC decision engine.

Precedence rule (evaluate everything, stop at the first thing that decides):

1. Load the subject's ABAC attributes (Attribute rows for user_id+tenant_id)
   into a flat `{key: value}` context. If `resource_attributes` was passed
   in, merge it on top — resource-specific context (the freshest, most
   relevant data for *this* decision) wins over a stale subject attribute
   with the same key.
2. Load this tenant's active AbacPolicy rows matching resource_type+action,
   ordered by priority DESC, then 'deny' before 'allow' at an equal
   priority (the safer tiebreak), then most-recently-created first (see
   PolicyRepository.list_matching). Evaluate each policy's condition tree
   against the context in that order; the first one whose conditions match
   decides the request — its effect (allow/deny) is the decision.
3. If no ABAC policy matched at all, fall back to plain RBAC: does any role
   assigned to the user carry a Permission named "{resource_type}:{action}"?
   If so, allow.
4. Otherwise, default-deny.

This means an explicit ABAC policy (allow or deny) always overrides the
RBAC fallback — ABAC is the refinement layer on top of RBAC's coarse
grant, not a separate parallel check. A policy with no `conditions` (None
or `{}`) matches unconditionally, i.e. it applies to every request for
its resource_type+action regardless of attributes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ConditionOperator, EntityStatus, PolicyEffect
from app.domain.exceptions import InvalidPolicyConditionError
from app.models.policy import AbacPolicy
from app.repositories.attribute import AttributeRepository
from app.repositories.policy import PolicyRepository
from app.repositories.role import RoleRepository

_MISSING = object()


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    matched_policy_id: uuid.UUID | None


class PolicyEvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policy_repo = PolicyRepository(session)
        self._attribute_repo = AttributeRepository(session)
        self._role_repo = RoleRepository(session)

    async def evaluate(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        resource_type: str,
        action: str,
        resource_attributes: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        attributes = await self._attribute_repo.list_for_user(tenant_id, user_id)
        context: dict[str, Any] = {a.key: a.value for a in attributes}
        if resource_attributes:
            context.update(resource_attributes)

        policies = await self._policy_repo.list_matching(
            tenant_id, resource_type=resource_type, action=action
        )
        for policy in policies:
            if _policy_matches(policy, context):
                return PolicyDecision(
                    allowed=policy.effect == PolicyEffect.ALLOW,
                    reason=f"policy:{policy.name}",
                    matched_policy_id=policy.id,
                )

        if await self._has_rbac_permission(tenant_id, user_id, resource_type, action):
            return PolicyDecision(
                allowed=True,
                reason="rbac_permission_grant",
                matched_policy_id=None,
            )

        return PolicyDecision(
            allowed=False,
            reason="no_matching_policy_and_no_rbac_permission",
            matched_policy_id=None,
        )

    async def _has_rbac_permission(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        resource_type: str,
        action: str,
    ) -> bool:
        permission_name = f"{resource_type}:{action}"
        roles = await self._role_repo.list_for_user(user_id, tenant_id)
        for role in roles:
            permissions = await self._role_repo.list_permissions(role.id)
            for permission in permissions:
                if (
                    permission.name == permission_name
                    and permission.status == EntityStatus.ACTIVE
                ):
                    return True
        return False


def _policy_matches(policy: AbacPolicy, context: dict[str, Any]) -> bool:
    if not policy.conditions:
        return True
    return _evaluate_condition(policy.conditions, context)


def _evaluate_condition(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    if "all" in condition:
        return all(_evaluate_condition(c, context) for c in condition["all"])
    if "any" in condition:
        return any(_evaluate_condition(c, context) for c in condition["any"])

    try:
        attribute = condition["attribute"]
        op = ConditionOperator(condition["op"])
    except KeyError as exc:
        raise InvalidPolicyConditionError(
            f"condition leaf missing {exc.args[0]!r}: {condition!r}"
        ) from exc
    except ValueError as exc:
        raise InvalidPolicyConditionError(str(exc)) from exc

    actual = context.get(attribute, _MISSING)

    if op == ConditionOperator.EXISTS:
        return actual is not _MISSING
    if actual is _MISSING:
        return False

    expected: Any = condition.get("value")
    if op == ConditionOperator.EQ:
        return bool(actual == expected)
    if op == ConditionOperator.NE:
        return bool(actual != expected)
    if op == ConditionOperator.IN:
        if not isinstance(expected, (list, tuple, set, str)):
            raise InvalidPolicyConditionError(
                f"'in' operator needs a list value, got {expected!r}"
            )
        return actual in expected
    if op == ConditionOperator.GT:
        return bool(actual > expected)
    if op == ConditionOperator.GTE:
        return bool(actual >= expected)
    if op == ConditionOperator.LT:
        return bool(actual < expected)
    if op == ConditionOperator.LTE:
        return bool(actual <= expected)

    raise InvalidPolicyConditionError(f"unhandled operator {op!r}")
