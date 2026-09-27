"""Finite, host-authorized maintenance actions; no shell, network, or model authority.

The embedding host must authenticate the owner before its supplied approval
callback ever returns true. Review labels and model text are not credentials.
Grants are single-use, operation-bound, expire, and never persist or survive a
provider swap/restart. The controller performs no background execution.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .durable import DurableRuntime
from .hashutil import sha256_obj


class MaintenanceDenied(PermissionError):
    """An operation lacked a current independent host authorization."""


@dataclass(frozen=True)
class _Grant:
    plan_sha256: str
    expires_at: float
    provider_epoch: int


class ScopedMaintenance:
    """Host-only, finite execution of four explicitly supported operations.

    Never pass a model-provided callback into this constructor. The host's
    authenticated approval callback MUST be independent of inference output.
    """

    ALLOWED = frozenset({"inspect", "archive", "restore", "review_conflict"})

    def __init__(
        self, runtime: DurableRuntime, *,
        approve_by_host: Callable[[dict[str, Any]], bool] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.runtime = runtime
        self._approve_by_host = approve_by_host
        self._clock = monotonic
        self._provider_epoch = id(runtime.provider)
        self._grants: dict[str, _Grant] = {}
        self.audit: list[dict[str, Any]] = []

    @classmethod
    def validate(cls, raw: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise ValueError("maintenance plan must be a mapping")
        action = raw.get("action")
        if action not in cls.ALLOWED or raw.get("schema") != "beastbox-maintenance-action-v1":
            raise ValueError("unsupported maintenance action/schema")
        allowed = {"schema", "action", "reviewer"}
        if action in {"archive", "restore"}:
            allowed |= {"memory_id", "reason"}
        if action == "review_conflict":
            allowed |= {"first_id", "second_id", "reason"}
        if set(raw) != allowed:
            raise ValueError("unexpected or missing maintenance action fields")
        reviewer = raw["reviewer"]
        if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 128:
            raise ValueError("reviewer label required; host must authenticate it independently")
        plan = dict(raw)
        plan["reviewer"] = reviewer.strip()
        if action in {"archive", "restore", "review_conflict"}:
            reason = raw["reason"]
            if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 512:
                raise ValueError("explicit reviewed reason required")
            plan["reason"] = reason.strip()
            ids = (raw["memory_id"],) if action in {"archive", "restore"} else (raw["first_id"], raw["second_id"])
            if any(type(value) is not int or value <= 0 for value in ids) or len(set(ids)) != len(ids):
                raise ValueError("valid, distinct memory ids required")
        return plan

    def preview(self, plan: Mapping[str, Any]) -> dict[str, Any]:
        validated = self.validate(plan)
        return {"valid": True, "requires_independent_host_approval": True,
                "action": validated["action"], "plan_sha256": sha256_obj(validated)}

    def approve(self, plan: Mapping[str, Any], *, ttl_seconds: float = 60.0) -> str:
        checked = self.validate(plan)
        if not isinstance(ttl_seconds, (int, float)) or not 0 < ttl_seconds <= 300:
            raise ValueError("grant lifetime must be between 0 and 300 seconds")
        if id(self.runtime.provider) != self._provider_epoch:
            self._grants.clear()
            raise MaintenanceDenied("provider changed; create a fresh host-controlled controller")
        if self._approve_by_host is None or self._approve_by_host(dict(checked)) is not True:
            raise MaintenanceDenied("independent owner approval missing")
        token = secrets.token_urlsafe(24)
        self._grants[token] = _Grant(sha256_obj(checked), self._clock() + float(ttl_seconds),
                                     self._provider_epoch)
        return token

    def revoke(self, token: str) -> None:
        self._grants.pop(token, None)

    def execute(self, token: str, plan: Mapping[str, Any]) -> dict[str, Any]:
        checked = self.validate(plan)
        if id(self.runtime.provider) != self._provider_epoch:
            self._grants.clear()
            raise MaintenanceDenied("model/provider swap revoked every previous maintenance grant")
        grant = self._grants.pop(token, None)
        if grant is None or grant.provider_epoch != self._provider_epoch:
            raise MaintenanceDenied("missing, spent or revoked maintenance grant")
        if self._clock() >= grant.expires_at:
            raise MaintenanceDenied("maintenance grant expired")
        if sha256_obj(checked) != grant.plan_sha256:
            raise MaintenanceDenied("requested action differs from approved plan")
        action = checked["action"]
        reviewer = checked["reviewer"]
        if action == "inspect":
            result = self.runtime.inspect()
        elif action == "archive":
            result = self.runtime.archive_memory(
                checked["memory_id"], reviewer=reviewer, reason=checked["reason"],
            )
        elif action == "restore":
            result = self.runtime.restore_memory(
                checked["memory_id"], reviewer=reviewer, reason=checked["reason"],
            )
        else:
            result = self.runtime.record_reviewed_contradiction(
                checked["first_id"], checked["second_id"],
                reviewer=reviewer, reason=checked["reason"],
            )
        self.audit.append({"action": action, "plan_sha256": grant.plan_sha256,
                           "result": "completed", "provider_epoch_changed": False})
        return result

    def execute_plan(self, plans: list[Mapping[str, Any]], tokens: list[str]) -> list[dict[str, Any]]:
        """Finite, ordered, fail-fast: prior committed actions aren't rolled back."""
        if not 1 <= len(plans) <= 8 or len(tokens) != len(plans):
            raise ValueError("maintenance plan must contain 1..8 individually approved actions")
        return [self.execute(token, plan) for token, plan in zip(tokens, plans, strict=True)]
