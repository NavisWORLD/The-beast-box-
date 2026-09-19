from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .dyn12 import update_dyn12

PHI = (1.0 + math.sqrt(5.0)) / 2.0


@dataclass
class CNS:
    """Seven-role software controller.

    Names mirror the documented COSMOS CNS roles: quantum, dark_matter, emeth,
    plasticity, awareness, daemons, surgeon. They are software metaphors, not
    claims of biological equivalence.
    """

    quantum: dict[str, Any] = field(default_factory=dict)
    dark_matter: dict[str, float] = field(default_factory=lambda: {"x": 1.0, "y": 1.0, "z": 1.0})
    emeth: dict[str, Any] = field(default_factory=dict)
    plasticity: dict[str, float] = field(default_factory=lambda: {"trust": 0.5})
    awareness: dict[str, Any] = field(default_factory=dict)
    daemons: list[str] = field(default_factory=list)
    surgeon: dict[str, Any] = field(default_factory=lambda: {"healthy": True, "faults": []})
    step: int = 0

    def _lorenz(self, dt: float = 0.01) -> None:
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        x, y, z = self.dark_matter["x"], self.dark_matter["y"], self.dark_matter["z"]
        dx = sigma * (y - x)
        dy = x * (rho - z) - y
        dz = x * y - beta * z
        self.dark_matter.update(x=x + dt * dx, y=y + dt * dy, z=z + dt * dz)

    def tick(self, mission_state, bridge_packet: dict[str, Any] | None = None) -> dict[str, Any]:
        self.step += 1
        packet = bridge_packet or {}
        self._lorenz()

        spark = [float(x) for x in packet.get("quantum_spark", [])]
        audio = [float(x) for x in packet.get("audio_features", [])]
        drive = spark + audio
        if not drive:
            drive = [self.dark_matter["x"] / 30.0, self.dark_matter["y"] / 30.0, self.dark_matter["z"] / 30.0]
        mission_state.dyn12 = update_dyn12(mission_state.dyn12, drive, step=self.step)

        # PHOS reference scalar: a bounded phi-scaffold readout, not the private PHOS model.
        mission_state.phos = sum(math.cos(PHI * x) for x in mission_state.dyn12) / 12.0

        self.quantum = {
            "spark_present": bool(spark),
            "spark_dim": len(spark),
            "provenance": packet.get("quantum_provenance", {}),
        }
        self.emeth = {
            "capsule_hash_present": bool(mission_state.provenance.get("capsule_hash")),
            "evidence_count": len(mission_state.evidence),
        }
        self.plasticity["trust"] = min(1.0, max(0.0, self.plasticity.get("trust", 0.5) + 0.01 * (1 if mission_state.evidence else -1)))
        self.awareness = {
            "mission_id": mission_state.mission_id,
            "current_step": mission_state.current_step,
            "pending": len(mission_state.pending_steps),
        }
        self.surgeon = {"healthy": True, "faults": []}
        return {
            "quantum": self.quantum,
            "dark_matter": dict(self.dark_matter),
            "emeth": self.emeth,
            "plasticity": dict(self.plasticity),
            "awareness": self.awareness,
            "daemons": list(self.daemons),
            "surgeon": self.surgeon,
            "dyn12": list(mission_state.dyn12),
            "phos": mission_state.phos,
        }
