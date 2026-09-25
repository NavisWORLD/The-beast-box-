"""Source-blind Quantum Buddy operator arms. Default modes are offline-only."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping

from .circuit import CIRCUIT_VERSION, build_qb_v1_manifest, simulate_qb_v1
from .hardware_gate import HardwareExecutionDisabled, HardwareExecutionPolicy
from .state import (
    BuddyQuantumState, BuddyStateError, MODES, canonical_vector_sha256,
    validate_vector12,
)

_HARDWARE = frozenset({"hardware_rigetti", "hardware_ibm"})


def _amplitude_matched_classical(dyn12, ideal_quantum12):
    """Deterministic nonlinear *classical* control matched by L2 amplitude.

    The matched target is the ideal entangled simulator packet for this same
    person state. No fitted weights, quantum hardware, or data leakage.
    """
    raw = [
        math.tanh(1.15 * v + 0.31 * dyn12[(i + 5) % 12]
                  - 0.18 * dyn12[(i * 7 + 1) % 12]
                  + 0.12 * math.cos((i+1) * .87))
        for i, v in enumerate(dyn12)
    ]
    # Keep every dimension available to achieve any target <= sqrt(12).
    raw = [v if abs(v) >= 1e-8 else (1e-8 if i % 2 else -1e-8)
           for i, v in enumerate(raw)]
    target = math.sqrt(sum(float(q)**2 for q in ideal_quantum12))
    if target <= 1e-14:
        return [0.0] * 12

    def scaled_norm(scale):
        return math.sqrt(sum(min(1.0, scale * abs(v))**2 for v in raw))

    low, high = 0.0, 1.0
    while scaled_norm(high) < target and high < 1e16:
        high *= 2
    if scaled_norm(high) + 1e-8 < target:
        raise BuddyStateError("classical amplitude-match infeasible")
    for _ in range(90):
        middle = (low + high)/2
        if scaled_norm(middle) < target:
            low = middle
        else:
            high = middle
    return [math.copysign(min(1.0, high*abs(v)), v) for v in raw]


class QuantumStateOperator:
    """One evaluator for classical, replay and ideal simulated controls.

    Hardware modes can only call an *injected* future executor after a distinct
    authorization policy; this class does not import or invoke provider SDKs.
    """

    def __init__(self, *, replay_bank: Mapping | None = None,
                 hardware_policy: HardwareExecutionPolicy | None = None,
                 hardware_executor=None):
        self.replay_bank = dict(replay_bank or {})
        self.hardware_policy = hardware_policy or HardwareExecutionPolicy()
        self.hardware_executor = hardware_executor

    def evaluate(self, dyn12, *, mode, circuit_version, shot_budget, provenance):
        vector = validate_vector12(dyn12, "dyn12")
        if mode not in MODES or circuit_version != CIRCUIT_VERSION:
            raise BuddyStateError("unsupported buddy mode or circuit version")
        if type(shot_budget) is not int or not 0 <= shot_budget <= 10_000_000:
            raise BuddyStateError("invalid circuit shot budget")
        if not isinstance(provenance, dict) or any(
                any(s in str(k).lower() for s in ("token","secret","credential","password"))
                for k in provenance):
            raise BuddyStateError("unsupported operator provenance")
        source = canonical_vector_sha256(vector)

        if mode in _HARDWARE:
            # Deny *before* accessing executor or contacting an SDK.
            self.hardware_policy.require_authorized()
            if self.hardware_executor is None:
                raise HardwareExecutionDisabled("no approved QPU executor installed")
            manifest = build_qb_v1_manifest(vector, entangled=True)
            result = self.hardware_executor.evaluate(
                vector, mode=mode, circuit_manifest=manifest,
                shot_budget=shot_budget, provenance=dict(provenance),
            )
            if (not isinstance(result, BuddyQuantumState) or result.mode != mode
                    or result.source_class != "hardware"
                    or result.source_state_sha256 != source
                    or result.circuit_sha256 != manifest.sha256):
                raise BuddyStateError("hardware executor returned unverified packet")
            return BuddyQuantumState.from_document(result.to_document())

        if mode == "off":
            packet = [0.0]*12
            backend = "off"
            circuit_sha = hashlib.sha256(b"qb-v1/off").hexdigest()
        elif mode == "replay":
            replay_key = provenance.get("replay_key")
            if not isinstance(replay_key, str) or replay_key not in self.replay_bank:
                raise BuddyStateError("archived replay key unavailable")
            # A replay from the same historical archive is intentionally not a
            # unique quantum identity. Label it as replay, never live hardware.
            archived = self.replay_bank[replay_key]
            if isinstance(archived, Mapping):
                packet = list(archived["qstate12"])
                backend = str(archived.get("backend", "archived"))
                circuit_sha = archived.get("circuit_sha256") or hashlib.sha256(
                    ("qb-v1/replay/"+replay_key).encode()).hexdigest()
            else:
                packet = list(archived)
                backend = "archived"
                circuit_sha = hashlib.sha256(
                    ("qb-v1/replay/"+replay_key).encode()).hexdigest()
            packet = validate_vector12(packet, "qstate12")
        else:
            ent = build_qb_v1_manifest(vector, entangled=True)
            if mode == "matched_classical":
                ez, ex = simulate_qb_v1(ent)
                packet = _amplitude_matched_classical(vector, ez+ex)
                backend = "local-nonlinear"
                circuit_sha = hashlib.sha256(
                    ("qb-v1/classical/"+source).encode()).hexdigest()
            else:
                manifest = ent if mode == "sim_entangled" else build_qb_v1_manifest(
                    vector, entangled=False,
                )
                z, x = simulate_qb_v1(manifest)
                packet = z + x
                backend = "local-statevector"
                circuit_sha = manifest.sha256
        source_class = {
            "off": "none",
            "matched_classical": "classical",
            "replay": "replay",
            "sim_unentangled": "simulator",
            "sim_entangled": "simulator",
        }[mode]
        return BuddyQuantumState.create(
            qstate12=packet, source_state_sha256=source,
            mode=mode, source_class=source_class, backend=backend,
            shot_count=0, circuit_version=CIRCUIT_VERSION,
            circuit_sha256=circuit_sha, job_id=None, valid_for_seconds=300,
        )
