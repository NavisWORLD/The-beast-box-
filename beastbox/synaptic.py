from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .state_family import StateFamily


@dataclass
class SynapticField:
    """Reference runtime binding state families, CNS summaries, and bridge data."""

    state_family: StateFamily = field(default_factory=StateFamily)
    last_packet: dict[str, Any] = field(default_factory=dict)

    def step(
        self,
        *,
        audio_features: list[float] | None = None,
        quantum_spark: list[float] | None = None,
        extra: list[float] | None = None,
        conditioning_vector: list[float] | None = None,
    ) -> dict[str, Any]:
        if conditioning_vector is not None:
            if (
                not isinstance(conditioning_vector, list)
                or len(conditioning_vector) != 12
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or abs(float(value)) > 1.0
                    for value in conditioning_vector
                )
            ):
                raise ValueError("conditioning_vector must contain 12 finite values in [-1,1]")
            drive = [float(value) for value in conditioning_vector]
        else:
            drive = list(audio_features or []) + list(quantum_spark or []) + list(extra or [])
        states = self.state_family.update(drive or [0.0])
        self.last_packet = {
            "drive_dimension": len(drive),
            "audio_dimension": len(audio_features or []),
            "quantum_dimension": len(quantum_spark or []),
            "states": states,
            "preflight": self.state_family.preflight(),
        }
        if conditioning_vector is not None:
            self.last_packet["conditioning_dimension"] = 12
            self.last_packet["drive_contract"] = "generic-model-control-C1..C12"
        return self.last_packet
