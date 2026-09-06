"""Explicit, bounded cloud probes. No fallback or credential-bearing receipts."""
from __future__ import annotations

import json
import math
import os
import re

from .events import normalize_event
from .hashutil import sha256_obj

RESOURCE_GROUPS = {
    "ibm": ("IBM_QUANTUM_TOKEN", "IBM_QUANTUM_INSTANCE", "IBM_QUANTUM_BACKEND"),
    "azure": ("AZURE_QUANTUM_RESOURCE_ID", "AZURE_QUANTUM_LOCATION", "AZURE_QUANTUM_TARGET"),
}
RESOURCE_ENV = tuple(key for group in RESOURCE_GROUPS.values() for key in group)


class ResourceUnavailable(RuntimeError):
    """Safe diagnostic: provider errors and credential values are never copied."""


def resource_status() -> dict:
    return {provider: {key: "configured" if os.environ.get(key, "").strip() else "missing"
                       for key in keys} for provider, keys in RESOURCE_GROUPS.items()}


def _label(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", value):
        raise ResourceUnavailable("Invalid provider receipt")
    secrets = [os.environ.get(key) for key in ("IBM_QUANTUM_TOKEN", "IBM_QUANTUM_INSTANCE",
                                               "AZURE_QUANTUM_RESOURCE_ID")]
    if any(secret and secret in value for secret in secrets):
        raise ResourceUnavailable("Invalid provider receipt")
    return value


def _event(metadata, probabilities):
    features = [2.0 * probabilities.get(format(i, "02b"), 0.) - 1. for i in range(4)]
    event = dict(schema="sensor-event-v1", source="software-event",
                 text=json.dumps(metadata, sort_keys=True, allow_nan=False), features=features)
    normalize_event(event)
    return event


def _ibm(shots):
    from . import quantum
    receipt = quantum.submit_real("01", shots=shots,
                                  backend_name=os.environ["IBM_QUANTUM_BACKEND"], confirm=True)
    job_id, backend = _label(receipt.job_id), _label(receipt.backend)
    if backend != os.environ["IBM_QUANTUM_BACKEND"] or receipt.shots != shots:
        raise ResourceUnavailable("Unexpected provider receipt")
    if not isinstance(receipt.circuit_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", receipt.circuit_sha256):
        raise ResourceUnavailable("Invalid circuit receipt")
    counts = quantum.retrieve_counts(job_id)
    if (not isinstance(counts, dict) or not counts or len(counts) > 4
            or any(k not in ("00", "01", "10", "11") or type(v) is not int or v < 0
                   for k, v in counts.items()) or sum(counts.values()) != shots):
        raise ResourceUnavailable("Invalid observed counts")
    return _event(dict(source="ibm-quantum", mode="REAL_IBM", result_kind="observed-counts",
                       native_job_id=job_id, backend=backend, shots=shots, counts=counts,
                       circuit_sha256=receipt.circuit_sha256, probe="two-qubit-HZH-phase-roundtrip"),
                  {k: v / shots for k, v in counts.items()})


def _azure(shots):
    try:
        from qdk.azure import Workspace
    except ImportError:
        raise ResourceUnavailable("Azure SDK unavailable; install qdk[azure]") from None
    target_name = os.environ["AZURE_QUANTUM_TARGET"]
    if target_name != "ionq.simulator":
        raise ResourceUnavailable("Azure target must be ionq.simulator")
    workspace = Workspace(resource_id=os.environ["AZURE_QUANTUM_RESOURCE_ID"],
                          location=os.environ["AZURE_QUANTUM_LOCATION"])
    target = workspace.get_targets(name=target_name)
    if target.name != target_name:
        raise ResourceUnavailable("Azure target mismatch")
    circuit = {"qubits": 2, "circuit": [{"gate": "h", "target": 0},
                                        {"gate": "cnot", "control": 0, "target": 1}]}
    job = target.submit(circuit, name="beastbox-bounded-probe", shots=shots)
    if job.details.target != target_name:
        raise ResourceUnavailable("Azure job target mismatch")
    job_id = _label(job.id)
    result = job.get_results(timeout_secs=120)
    histogram = result.get("histogram") if isinstance(result, dict) else None
    if not isinstance(histogram, dict) or not histogram or len(histogram) > 4:
        raise ResourceUnavailable("Invalid probability distribution")
    probabilities = {}
    for key, value in histogram.items():
        if (key not in ("0", "1", "2", "3") or isinstance(value, bool)
                or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 1):
            raise ResourceUnavailable("Invalid probability distribution")
        probabilities[format(int(key), "02b")] = float(value)
    if not math.isclose(sum(probabilities.values()), 1., rel_tol=0., abs_tol=1e-6):
        raise ResourceUnavailable("Invalid probability distribution")
    return _event(dict(source="azure-quantum", mode="AZURE_IONQ_SIMULATOR", result_kind="probabilities",
                       native_job_id=job_id, backend=target_name, shots_requested=shots,
                       probabilities=probabilities, circuit_sha256=sha256_obj(circuit),
                       probe="two-qubit-Bell-distribution"), probabilities)


def quantum_event(provider, shots=128, allow_live=False):
    """Submit one authorized job; even a cloud simulator requires literal True."""
    if allow_live is not True:
        raise ResourceUnavailable("Cloud submission requires allow_live=True")
    if type(shots) is not int or not 1 <= shots <= 1024:
        raise ValueError("shots must be an integer in 1..1024")
    if provider not in ("ibm", "azure"):
        raise ValueError("provider must be ibm or azure")
    required = ("IBM_QUANTUM_TOKEN", "IBM_QUANTUM_BACKEND") if provider == "ibm" else RESOURCE_GROUPS["azure"]
    if any(not os.environ.get(key, "").strip() for key in required):
        raise ResourceUnavailable("Missing provider configuration")
    # Suppress SDK exception chaining as tracebacks can contain tokens or URLs.
    try:
        return _ibm(shots) if provider == "ibm" else _azure(shots)
    except ResourceUnavailable:
        raise
    except Exception:
        raise ResourceUnavailable("Provider operation failed; no fallback was performed") from None
