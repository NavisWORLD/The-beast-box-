"""Separate policy gate: experimental hardware submission is disabled by default."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .circuit import CircuitManifest
    from .state import BuddyQuantumState


class HardwareExecutionDisabled(RuntimeError):
    """A deliberately non-recoverable denial; the caller must not auto-fallback."""


@dataclass(frozen=True)
class HardwareExecutionPolicy:
    allow_live: bool = False
    cost_verified: bool = False
    human_approved: bool = False

    def require_authorized(self) -> None:
        if self.allow_live is not True:
            raise HardwareExecutionDisabled("live hardware submission disabled")
        if self.cost_verified is not True:
            raise HardwareExecutionDisabled("target costs and credit status not verified")
        if self.human_approved is not True:
            raise HardwareExecutionDisabled("fresh QPU job requires explicit owner approval")


class HardwareExecutor(Protocol):
    def evaluate(self, dyn12, *, mode: str, circuit_manifest: CircuitManifest,
                 shot_budget: int, provenance: dict) -> BuddyQuantumState:
        """Adapter implemented only in the separately authorized hardware phase."""
