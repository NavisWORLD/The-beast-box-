from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .hashutil import sha256_obj


@dataclass
class BridgePacket:
    audio_features: list[float] = field(default_factory=list)
    quantum_spark: list[float] = field(default_factory=list)
    quantum_provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def safe_dict(self) -> dict[str, Any]:
        data = {
            "audio_features": [float(x) for x in self.audio_features],
            "quantum_spark": [float(x) for x in self.quantum_spark],
            "quantum_provenance": dict(self.quantum_provenance),
            "metadata": dict(self.metadata),
        }
        for forbidden in ("token", "credential", "password", "secret", "authorization"):
            for key in list(data["metadata"]):
                if forbidden in key.lower():
                    data["metadata"].pop(key, None)
        data["packet_sha256"] = sha256_obj(data)
        return data


def spark_from_counts(counts: dict[str, int], dimensions: int = 12) -> list[float]:
    """Deterministic bounded measurement summary in [-1, 1].

    This does not claim quantum advantage; it only converts a histogram into a
    reproducible numerical control vector.
    """
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    total = sum(int(v) for v in counts.values())
    if total <= 0:
        return [0.0] * dimensions
    width = max((len(k.replace(" ", "")) for k in counts), default=1)
    expectations: list[float] = []
    for bit in range(width):
        one = 0
        for raw, n in counts.items():
            s = raw.replace(" ", "").zfill(width)
            if s[-1 - bit] == "1":
                one += int(n)
        p1 = one / total
        expectations.append(1.0 - 2.0 * p1)
    out: list[float] = []
    for i in range(dimensions):
        a = expectations[i % len(expectations)]
        b = expectations[(i * 3 + 1) % len(expectations)]
        out.append(max(-1.0, min(1.0, 0.7 * a + 0.3 * b)))
    return out
