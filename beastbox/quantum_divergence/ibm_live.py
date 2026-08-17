from __future__ import annotations

import hashlib
from typing import Any

from beastbox.quantum import IBMReceipt, _backend, _imports, _service, _bitarray_counts

from .entropy import EntropyReceipt, quantum_entropy_from_counts


def build_entropy_circuit(width: int = 12):
    if int(width) <= 0:
        raise ValueError("entropy width must be positive")
    QuantumCircuit, _, _, _, _ = _imports()
    qc = QuantumCircuit(int(width), int(width), name="beastbox_tears_in_rain_entropy")
    for i in range(int(width)):
        qc.h(i)
    qc.measure(range(int(width)), range(int(width)))
    return qc


def submit_real_entropy(
    *,
    width: int = 12,
    shots: int = 2048,
    backend_name: str | None = None,
    confirm: bool = False,
) -> IBMReceipt:
    """Submit a Hadamard-measurement entropy workload to real IBM hardware."""
    if not confirm:
        raise RuntimeError("real IBM entropy submission requires confirm=True after human approval")
    if int(shots) <= 0:
        raise ValueError("shots must be positive")

    _, qasm3, generate_preset_pass_manager, _, SamplerV2 = _imports()
    service = _service()
    backend = _backend(service, int(width), backend_name)
    qc = build_entropy_circuit(int(width))
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa = pm.run(qc)
    circuit_sha = hashlib.sha256(qasm3.dumps(isa).encode("utf-8")).hexdigest()
    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa], shots=int(shots))
    backend_label = str(getattr(backend, "name", backend_name or "unknown"))
    return IBMReceipt(
        job_id=job.job_id(),
        backend=backend_label,
        shots=int(shots),
        circuit_sha256=circuit_sha,
        pubs=1,
    )


def retrieve_real_entropy(receipt: IBMReceipt, dimensions: int = 12) -> tuple[EntropyReceipt, dict[str, int]]:
    """Retrieve IBM-native counts and transform them into the bounded wave."""
    service = _service()
    job = service.job(receipt.job_id)
    result = job.result()
    if not result:
        raise RuntimeError("IBM entropy job returned no primitive result")
    counts = _bitarray_counts(result[0].data)
    provenance: dict[str, Any] = receipt.to_dict()
    entropy = quantum_entropy_from_counts(counts, provenance, dimensions=dimensions)
    return entropy, counts
