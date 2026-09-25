"""Frozen qb-v1 six-qubit circuit and dependency-free ideal statevector replay.

Qubit q is little-endian bit q in the 64-amplitude vector. Readout packet order
is always [Z0..Z5, X0..X5]. No QPU, cloud account, or provider SDK is accessed.
"""
from __future__ import annotations

import cmath
import hashlib
import json
import math
import struct
from dataclasses import dataclass

from .state import validate_vector12

QUBITS = 6
CIRCUIT_VERSION = "qb-v1"


@dataclass(frozen=True)
class CircuitManifest:
    version: str
    qubits: int
    entangled: bool
    operations: tuple[tuple, ...]
    sha256: str

    @property
    def rotation_count(self) -> int:
        return sum(g[0] in ("RY", "RZ") for g in self.operations)

    @property
    def cnot_count(self) -> int:
        return sum(g[0] == "CNOT" for g in self.operations)

    def to_quil(self, *, basis: str) -> str:
        if basis not in ("X", "Z"):
            raise ValueError("qb-v1 measures only joint X or joint Z basis")
        lines = ["DECLARE ro BIT[6]"]
        for op in self.operations:
            if op[0] == "CNOT":
                lines.append(f"CNOT {op[1]} {op[2]}")
            else:
                lines.append(f"{op[0]}({op[2]:.17g}) {op[1]}")
        if basis == "X":
            lines.extend(f"H {q}" for q in range(self.qubits))
        lines.extend(f"MEASURE {q} ro[{q}]" for q in range(self.qubits))
        return "\n".join(lines) + "\n"


def build_qb_v1_manifest(dyn12, *, entangled: bool) -> CircuitManifest:
    if type(entangled) is not bool:
        raise ValueError("entangled must be boolean")
    raw = validate_vector12(dyn12, "dyn12")
    # This is also the input representation of canonical_vector_sha256.
    v = struct.unpack("<12f", struct.pack("<12f", *raw))
    ops = []
    for q in range(QUBITS):
        ops.extend((("RY", q, math.pi * v[q]), ("RZ", q, math.pi * v[6 + q])))
    if entangled:
        ops.extend(("CNOT", q, (q + 1) % QUBITS) for q in range(QUBITS))
    for q in range(QUBITS):
        ops.extend((("RY", q, math.pi * v[5 - q]), ("RZ", q, math.pi * v[11 - q])))
    if entangled:
        ops.extend(("CNOT", (q + 1) % QUBITS, q) for q in range(QUBITS))
    canonical = json.dumps(
        {"version": CIRCUIT_VERSION, "qubits": QUBITS, "entangled": entangled,
         "operations": ops}, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return CircuitManifest(
        CIRCUIT_VERSION, QUBITS, entangled, tuple(ops),
        hashlib.sha256(canonical).hexdigest(),
    )


def simulate_qb_v1(manifest: CircuitManifest) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Exactly simulate ideal joint amplitudes, not 12 independent marginal coins."""
    if (not isinstance(manifest, CircuitManifest) or manifest.version != CIRCUIT_VERSION
            or manifest.qubits != QUBITS or manifest.rotation_count != 24
            or manifest.cnot_count != (12 if manifest.entangled else 0)):
        raise ValueError("invalid frozen qb-v1 circuit")
    amps = [0j] * (1 << QUBITS)
    amps[0] = 1+0j
    for gate in manifest.operations:
        name, q, value = gate
        bit = 1 << q
        if name == "CNOT":
            target_bit = 1 << value
            if q == value or not 0 <= q < QUBITS or not 0 <= value < QUBITS:
                raise ValueError("invalid frozen CNOT")
            for i in range(len(amps)):
                if i & bit and not (i & target_bit):
                    j = i | target_bit
                    amps[i], amps[j] = amps[j], amps[i]
            continue
        if not 0 <= q < QUBITS or not math.isfinite(value):
            raise ValueError("invalid rotation")
        if name == "RY":
            cosine, sine = math.cos(value / 2), math.sin(value / 2)
            for i in range(len(amps)):
                if not (i & bit):
                    j = i | bit
                    a, b = amps[i], amps[j]
                    amps[i], amps[j] = cosine * a - sine * b, sine * a + cosine * b
        elif name == "RZ":
            p0, p1 = cmath.exp(-1j * value / 2), cmath.exp(1j * value / 2)
            for i in range(len(amps)):
                amps[i] *= p1 if i & bit else p0
        else:
            raise ValueError("unsupported frozen circuit gate")
    z = []
    x = []
    for q in range(QUBITS):
        bit = 1 << q
        z.append(sum((1 if not i & bit else -1) * abs(a)**2
                     for i, a in enumerate(amps)))
        x.append(2 * sum((amps[i].conjugate() * amps[i | bit]).real
                         for i in range(len(amps)) if not i & bit))
    return (tuple(max(-1.0, min(1.0, v)) for v in z),
            tuple(max(-1.0, min(1.0, v)) for v in x))
