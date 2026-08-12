from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class IBMReceipt:
    job_id: str
    backend: str
    shots: int
    circuit_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ibm_native_job_id": self.job_id,
            "backend": self.backend,
            "shots": self.shots,
            "circuit_sha256": self.circuit_sha256,
        }


def _imports():
    try:
        from qiskit import QuantumCircuit, qasm3
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError as exc:
        raise RuntimeError("Install quantum extras: pip install 'cosmos-beast-box[quantum]'") from exc
    return QuantumCircuit, qasm3, generate_preset_pass_manager, QiskitRuntimeService, SamplerV2


def build_phase_roundtrip(bits: str):
    QuantumCircuit, _, _, _, _ = _imports()
    if not bits or any(b not in "01" for b in bits):
        raise ValueError("bits must be a non-empty binary string")
    qc = QuantumCircuit(len(bits), len(bits))
    # Logical bit i maps to qubit i and classical bit i. Count display endianness
    # is handled by per-classical-bit extraction downstream, not visual guessing.
    for i, b in enumerate(bits):
        qc.h(i)
        if b == "1":
            qc.z(i)
        qc.h(i)
    qc.measure(range(len(bits)), range(len(bits)))
    return qc


def _service():
    _, _, _, QiskitRuntimeService, _ = _imports()
    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is not set")
    kwargs: dict[str, Any] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE")
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def submit_real(bits: str, shots: int = 1024, backend_name: str | None = None, confirm: bool = False) -> IBMReceipt:
    """Host-side, explicit opt-in IBM submission. Never call this from the box."""
    if not confirm:
        raise RuntimeError("real IBM submission requires confirm=True after human approval")
    _, qasm3, generate_preset_pass_manager, _, SamplerV2 = _imports()
    service = _service()
    if backend_name:
        backend = service.backend(backend_name)
    else:
        backend = service.least_busy(min_num_qubits=len(bits), operational=True, simulator=False)
    if getattr(backend.configuration(), "simulator", False):
        raise RuntimeError("REAL_IBM path rejected simulator backend")

    logical = build_phase_roundtrip(bits)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa = pm.run(logical)
    circuit_text = qasm3.dumps(isa)
    circuit_sha = hashlib.sha256(circuit_text.encode()).hexdigest()
    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa], shots=shots)
    return IBMReceipt(job_id=job.job_id(), backend=backend.name, shots=shots, circuit_sha256=circuit_sha)


def retrieve_counts(job_id: str) -> dict[str, int]:
    """Fresh-service remote retrieval by IBM-native job ID."""
    service = _service()
    job = service.job(job_id)
    result = job.result()
    if not result:
        raise RuntimeError("IBM job returned no primitive results")
    pub = result[0]
    data = pub.data
    # SamplerV2 DataBin fields vary with classical register names. Find the
    # first returned BitArray-like field exposing get_counts().
    for name in dir(data):
        if name.startswith("_"):
            continue
        try:
            value = getattr(data, name)
        except Exception:
            continue
        if hasattr(value, "get_counts"):
            counts = value.get_counts()
            return {str(k): int(v) for k, v in counts.items()}
    raise RuntimeError("could not locate a BitArray/get_counts field in IBM result")


def majority_decode(counts: dict[str, int], width: int) -> str:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("empty counts")
    bits = []
    for logical in range(width):
        zeros = ones = 0
        for raw, n in counts.items():
            s = raw.replace(" ", "").zfill(width)
            bit = s[-1 - logical]
            if bit == "1":
                ones += n
            else:
                zeros += n
        if ones == zeros:
            raise ValueError("majority decode tie")
        bits.append("1" if ones > zeros else "0")
    return "".join(bits)
