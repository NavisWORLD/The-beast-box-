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
    pubs: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "ibm_native_job_id": self.job_id,
            "backend": self.backend,
            "shots_per_pub": self.shots,
            "circuit_sha256": self.circuit_sha256,
            "pubs": self.pubs,
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
    qc = QuantumCircuit(len(bits), len(bits), name="beastbox_hzh_payload")
    # Logical bit i maps to qubit/classical bit i. Printed count strings are
    # decoded per classical bit downstream rather than guessed visually.
    for i, b in enumerate(bits):
        qc.h(i)
        if b == "1":
            qc.z(i)
        qc.h(i)
    qc.measure(range(len(bits)), range(len(bits)))
    return qc


def _service():
    _, _, _, QiskitRuntimeService, _ = _imports()
    token = (os.environ.get("IBM_QUANTUM_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is not set")
    kwargs: dict[str, Any] = {"channel": "ibm_quantum_platform", "token": token}
    instance = (os.environ.get("IBM_QUANTUM_INSTANCE") or "").strip()
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def _backend(service, min_qubits: int, backend_name: str | None):
    if backend_name:
        backend = service.backend(backend_name)
        config = getattr(backend, "configuration", None)
        if callable(config) and bool(getattr(config(), "simulator", False)):
            raise RuntimeError("REAL_IBM path rejected simulator backend")
        if int(getattr(backend, "num_qubits", min_qubits)) < min_qubits:
            raise RuntimeError("selected backend does not have enough qubits")
        return backend
    return service.least_busy(min_num_qubits=min_qubits, operational=True, simulator=False)


def _bitarray_counts(data) -> dict[str, int]:
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


def submit_real(bits: str, shots: int = 1024, backend_name: str | None = None, confirm: bool = False) -> IBMReceipt:
    return submit_real_chunks([bits], shots=shots, backend_name=backend_name, confirm=confirm)


def submit_real_chunks(chunks: list[str], shots: int = 1024, backend_name: str | None = None, confirm: bool = False) -> IBMReceipt:
    """Submit multiple payload chunks as SamplerV2 PUBs in one authorized job.

    IBM credentials remain host-side. This function exposes no arbitrary IBM
    operation to the contained agent.
    """
    if not confirm:
        raise RuntimeError("real IBM submission requires confirm=True after human approval")
    if not chunks or any(not c or any(b not in "01" for b in c) for c in chunks):
        raise ValueError("chunks must be non-empty binary strings")
    width = max(len(c) for c in chunks)
    if any(len(c) != width for c in chunks):
        raise ValueError("all chunks must use the same bit width")
    _, qasm3, generate_preset_pass_manager, _, SamplerV2 = _imports()
    service = _service()
    backend = _backend(service, width, backend_name)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa_circuits = [pm.run(build_phase_roundtrip(bits)) for bits in chunks]
    circuit_manifest = [qasm3.dumps(circuit) for circuit in isa_circuits]
    circuit_sha = hashlib.sha256("\n---PUB---\n".join(circuit_manifest).encode("utf-8")).hexdigest()
    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa_circuits, shots=shots)
    backend_label = str(getattr(backend, "name", backend_name or "unknown"))
    return IBMReceipt(job_id=job.job_id(), backend=backend_label, shots=shots, circuit_sha256=circuit_sha, pubs=len(chunks))


def retrieve_pub_counts(job_id: str) -> list[dict[str, int]]:
    """Fresh-service remote retrieval by IBM-native RuntimeJobV2 ID."""
    service = _service()
    job = service.job(job_id)
    result = job.result()
    if not result:
        raise RuntimeError("IBM job returned no primitive results")
    return [_bitarray_counts(pub.data) for pub in result]


def retrieve_counts(job_id: str) -> dict[str, int]:
    pubs = retrieve_pub_counts(job_id)
    if not pubs:
        raise RuntimeError("IBM job returned no PUB results")
    return pubs[0]


def majority_decode(counts: dict[str, int], width: int) -> str:
    total = sum(int(v) for v in counts.values())
    if total <= 0:
        raise ValueError("empty counts")
    bits = []
    for logical in range(width):
        zeros = ones = 0
        for raw, n in counts.items():
            s = raw.replace(" ", "").zfill(width)
            bit = s[-1 - logical]
            if bit == "1":
                ones += int(n)
            else:
                zeros += int(n)
        if ones == zeros:
            raise ValueError("majority decode tie")
        bits.append("1" if ones > zeros else "0")
    return "".join(bits)
