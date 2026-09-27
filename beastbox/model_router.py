"""Explicit host-selected model capability routing over ONE existing durable runtime.

No heuristic winner or trained routing advantage is claimed. Labels/capability
declarations are operator configuration, not verified model abilities. Host
approval is independent of model output; missing capability and failed
providers NEVER cause a hidden security or model fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .durable import DurableRuntime
from .providers import TextProvider


class RoutingDenied(PermissionError):
    """Missing independent host permission or invalid provider capability."""


@dataclass(frozen=True)
class ModelSlot:
    key: str
    provider: TextProvider
    capabilities: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key or len(self.key) > 128:
            raise ValueError("model slot label must be a bounded non-empty identifier")
        if not callable(getattr(self.provider, "generate", None)):
            raise ValueError("a model slot must supply a text-provider generate method")
        if (not isinstance(self.capabilities, frozenset) or not self.capabilities
                or any(not isinstance(c, str) or not c or len(c) > 64 for c in self.capabilities)):
            raise ValueError("model capabilities must be explicit bounded strings")


class ModelRouter:
    """Owner-controlled active model router; state/memory/authority stay outside slots."""

    def __init__(
        self, runtime: DurableRuntime, slots: Iterable[ModelSlot], *,
        authorize_by_host: Callable[[str, str], bool] | None = None,
    ) -> None:
        self.runtime = runtime
        self.slots: dict[str, ModelSlot] = {}
        for slot in slots:
            if slot.key in self.slots:
                raise ValueError("duplicate model slot labels are forbidden")
            self.slots[slot.key] = slot
        if not self.slots:
            raise ValueError("a model router requires at least one registered provider")
        self._authorize_by_host = authorize_by_host
        self.active_key: str | None = None
        self._provider_generation: int | None = None
        self.handoffs: list[dict[str, Any]] = []

    def activate(self, key: str, *, capability: str) -> dict[str, Any]:
        slot = self.slots.get(key)
        if slot is None or capability not in slot.capabilities:
            raise RoutingDenied("selected slot does not provide the requested declared capability")
        if self._authorize_by_host is None or self._authorize_by_host(key, capability) is not True:
            raise RoutingDenied("independent host approval missing for selected model route")
        previous = self.runtime.inspect()  # includes exact optional external-anchor checks
        self.active_key = None
        self._provider_generation = None
        self.runtime.swap_provider(slot.provider)  # also revokes pre-existing tool grants
        after = self.runtime.inspect()
        for field in ("system_id", "checkpoint_sha256", "sequence", "memory_digest", "state_sha256"):
            if previous[field] != after[field]:
                raise RuntimeError("model activation altered persistent runtime state: " + field)
        self.active_key = key
        self._provider_generation = self.runtime._provider_generation
        receipt = {
            "schema": "configured-model-route-v1",
            "provider_slot": key,
            "capability": capability,
            "state_unchanged": True,
            "tool_grants_revoked": True,
            "weight_hash_attested": False,
        }
        self.handoffs.append(receipt)
        return dict(receipt)

    def respond(self, text: str, *, capability: str) -> dict[str, Any]:
        if self.active_key is None or self._provider_generation != self.runtime._provider_generation:
            self.active_key = None
            raise RoutingDenied("no active host-approved route or provider was swapped externally")
        if capability not in self.slots[self.active_key].capabilities:
            raise RoutingDenied("requested capability differs from active model route")
        result = self.runtime.respond(text)
        return {**result, "configured_model_slot": self.active_key,
                "capability_declaration_verified": False}
