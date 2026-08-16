from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Iterable


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def tears_in_rain_wave(values: Iterable[float]) -> tuple[float, ...]:
    out: list[float] = []
    for value in values:
        x = float(value)
        if not math.isfinite(x):
            raise ValueError("tears in the rain wave requires finite values")
        out.append(max(-1.0, min(1.0, x)))
    return tuple(out)


@dataclass(frozen=True)
class EntropyReceipt:
    source: str
    vector: tuple[float, ...]
    source_sha256: str
    provenance: dict[str, Any]


def classical_entropy(seed: int, dimensions: int = 12) -> EntropyReceipt:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    rng = random.Random(int(seed))
    vector = tears_in_rain_wave(rng.uniform(-1.0, 1.0) for _ in range(dimensions))
    provenance = {"seed": int(seed), "dimensions": int(dimensions), "algorithm": "python-random-mt19937"}
    return EntropyReceipt("classical-prng", vector, _sha({"provenance": provenance, "vector": vector}), provenance)


def _validate_real_ibm_provenance(provenance: dict[str, Any]) -> None:
    required = ("ibm_native_job_id", "backend", "shots_per_pub", "circuit_sha256")
    if any(not provenance.get(key) for key in required):
        raise ValueError("quantum entropy requires complete real IBM provenance")
    backend = str(provenance["backend"]).lower()
    if "simulator" in backend or backend.startswith("aer") or backend.startswith("fake"):
        raise ValueError("quantum entropy requires a real IBM hardware backend")
    if int(provenance["shots_per_pub"]) <= 0:
        raise ValueError("quantum entropy requires positive IBM shots")


def quantum_entropy_from_counts(
    counts: dict[str, int], provenance: dict[str, Any], dimensions: int = 12
) -> EntropyReceipt:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    _validate_real_ibm_provenance(provenance)
    clean = {str(k).replace(" ", ""): int(v) for k, v in counts.items() if int(v) >= 0}
    total = sum(clean.values())
    if total <= 0:
        raise ValueError("quantum entropy requires non-empty measurement counts")
    width = max((len(k) for k in clean), default=0)
    if width <= 0 or any(set(k) - {"0", "1"} for k in clean):
        raise ValueError("IBM counts must use binary bitstrings")

    expectations: list[float] = []
    for logical in range(width):
        ones = 0
        for raw, n in clean.items():
            if raw.zfill(width)[-1 - logical] == "1":
                ones += n
        expectations.append(1.0 - 2.0 * (ones / total))

    expanded = []
    for i in range(dimensions):
        a = expectations[i % width]
        b = expectations[(i * 3 + 1) % width]
        c = expectations[(i * 5 + 2) % width]
        expanded.append(0.55 * a + 0.30 * b + 0.15 * c)
    vector = tears_in_rain_wave(expanded)
    source_material = {"counts": clean, "provenance": provenance, "dimensions": dimensions, "vector": vector}
    return EntropyReceipt("ibm-quantum-hardware", vector, _sha(source_material), dict(provenance))
