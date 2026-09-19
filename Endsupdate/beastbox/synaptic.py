from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .state_family import StateFamily


@dataclass
class SynapticField:
    """Reference runtime binding state families, CNS summaries, and bridge data."""

    state_family: StateFamily = field(default_factory=StateFamily)
    last_packet: dict[str, Any] = field(default_factory=dict)

    def step(self, *, audio_features: list[float] | None = None, quantum_spark: list[float] | None = None, extra: list[float] | None = None) -> dict[str, Any]:
        drive = list(audio_features or []) + list(quantum_spark or []) + list(extra or [])
        states = self.state_family.update(drive or [0.0])
        self.last_packet = {
            "drive_dimension": len(drive),
            "audio_dimension": len(audio_features or []),
            "quantum_dimension": len(quantum_spark or []),
            "states": states,
            "preflight": self.state_family.preflight(),
        }
        return self.last_packet
