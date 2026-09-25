from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .quantum_buddy.state import validate_vector12
from .state_family import StateFamily


@dataclass
class SynapticField:
    """Reference runtime binding state families, CNS summaries, and bridge data."""

    state_family: StateFamily = field(default_factory=StateFamily)
    last_packet: dict[str, Any] = field(default_factory=dict)

    def step(self, *, audio_features: list[float] | None = None,
             quantum_spark: list[float] | None = None,
             extra: list[float] | None = None,
             person_state12: list[float] | None = None,
             buddy_metric12: list[float] | None = None) -> dict[str, Any]:
        """Use a distinct person-state drive; qstate is only an attention metric."""
        if buddy_metric12 is not None:
            validate_vector12(buddy_metric12, "buddy_metric12")
        explicit_person = person_state12 is not None
        if explicit_person:
            drive = list(validate_vector12(person_state12, "person_state12"))
        else:
            # Preserve existing legacy drive semantics for historical replay.
            drive = list(audio_features or []) + list(quantum_spark or []) + list(extra or [])
        states = self.state_family.update(drive or [0.0])
        self.last_packet = {
            "drive_dimension": len(drive),
            "audio_dimension": len(audio_features or []),
            "quantum_dimension": len(quantum_spark or []),
            "person_state_present": explicit_person,
            "person_state_dimension": 12 if explicit_person else 0,
            "buddy_metric_present": buddy_metric12 is not None,
            "legacy_drive_used": not explicit_person,
            "states": states,
            "preflight": self.state_family.preflight(),
        }
        return self.last_packet
