"""Models are mouths: MODEL != MEMORY != STATE != AUTHORITY.

Label: PORT of CORY ORIGINAL rules from beastbox/model_router.py (lines 1-92): explicit owner/host-approved
activation per slot + declared capability, no heuristic winner, a failed or missing provider NEVER falls back to
another one, and swapping a model must not change persistent state (checked by hashing memory + state before and
after). Providers are CORY ORIGINAL, vendored unmodified: providers.LocalOllamaProvider (loopback-only, no
redirects) and providers.ReferenceTextProvider. The router class here is AI-written (his ModelRouter needs his full
DurableRuntime, which the Spark host does not carry).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .beastbox_vendor.providers import LocalOllamaProvider, ReferenceTextProvider  # noqa: F401  (re-export)


class Mouth(Protocol):
    def generate(self, prompt: str) -> str: ...


class MouthDenied(PermissionError):
    pass


@dataclass(frozen=True)
class MouthSlot:
    key: str
    provider: Mouth
    capabilities: frozenset[str]


class MouthRouter:
    def __init__(self, slots: list[MouthSlot], *, approve: Callable[[str, str], bool] | None,
                 state_digest: Callable[[], str]):
        self.slots = {}
        for s in slots:
            if s.key in self.slots:
                raise ValueError("duplicate mouth slot")
            self.slots[s.key] = s
        if not self.slots:
            raise ValueError("at least one mouth required")
        self._approve = approve
        self._digest = state_digest
        self.active: str | None = None
        self.handoffs: list[dict[str, Any]] = []

    def activate(self, key: str, *, capability: str = "chat") -> dict[str, Any]:
        slot = self.slots.get(key)
        if slot is None or capability not in slot.capabilities:
            raise MouthDenied("slot does not declare that capability")
        if self._approve is None or self._approve(key, capability) is not True:
            raise MouthDenied("owner approval missing for this mouth")
        before = self._digest()
        self.active = key
        after = self._digest()
        if before != after:
            raise RuntimeError("switching mouths changed memory/state")
        receipt = {"schema": "spark-mouth-route-v1", "slot": key, "capability": capability,
                   "state_unchanged": True, "state_sha256": after, "weight_hash_attested": False}
        self.handoffs.append(receipt)
        return receipt

    def speak(self, prompt: str, *, capability: str = "chat") -> dict[str, Any]:
        if self.active is None:
            raise MouthDenied("no owner-approved mouth is active")
        slot = self.slots[self.active]
        if capability not in slot.capabilities:
            raise MouthDenied("active mouth does not declare this capability")
        text = slot.provider.generate(prompt)  # errors propagate: NO silent fallback to another mouth
        if not isinstance(text, str):
            raise TypeError("mouth returned non-text")
        return {"text": text, "mouth": self.active, "capability_declaration_verified": False}
