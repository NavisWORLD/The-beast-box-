"""Frozen qb-v1: deterministic software control arms and no hardware submission."""
import math

import pytest

from beastbox.quantum_buddy.circuit import build_qb_v1_manifest, simulate_qb_v1
from beastbox.quantum_buddy.hardware_gate import (
    HardwareExecutionDisabled, HardwareExecutionPolicy,
)
from beastbox.quantum_buddy.operators import QuantumStateOperator
from beastbox.quantum_buddy.state import BuddyQuantumState, BuddyStateError


PERSON = [0.08, -0.32, 0.47, -0.29, 0.16, -0.54,
          0.33, -0.11, 0.28, -0.43, 0.55, -0.18]


def operator():
    return QuantumStateOperator(replay_bank={"fixture": [0.2, -0.1] * 6})


def test_frozen_qb_v1_circuit_shape_hash_and_two_measurement_bases():
    ent = build_qb_v1_manifest(PERSON, entangled=True)
    no_ent = build_qb_v1_manifest(PERSON, entangled=False)
    assert ent.qubits == no_ent.qubits == 6
    assert ent.rotation_count == no_ent.rotation_count == 24
    assert ent.cnot_count == 12 and no_ent.cnot_count == 0
    assert len(ent.sha256) == 64 and ent.sha256 != no_ent.sha256
    assert ent.sha256 == build_qb_v1_manifest(list(PERSON), entangled=True).sha256
    for basis in ("Z", "X"):
        quil = ent.to_quil(basis=basis)
        assert quil.count("MEASURE ") == 6
        assert "DECLARE ro BIT[6]" in quil
        assert quil.count("CNOT ") == 12
        if basis == "X":
            assert quil.count("H ") == 6
    with pytest.raises(ValueError):
        ent.to_quil(basis="Y")


def test_joint_statevector_zero_parameters_have_expected_xz_observables():
    z, x = simulate_qb_v1(build_qb_v1_manifest([0.0]*12, entangled=True))
    assert len(z) == len(x) == 6
    assert z == pytest.approx([1.0]*6, abs=1e-12)
    assert x == pytest.approx([0.0]*6, abs=1e-12)


def test_entangled_and_unentangled_states_use_same_rotations_but_differ_on_input():
    ent = build_qb_v1_manifest(PERSON, entangled=True)
    no_ent = build_qb_v1_manifest(PERSON, entangled=False)
    assert [g for g in ent.operations if g[0] != "CNOT"] == [
        g for g in no_ent.operations if g[0] != "CNOT"
    ]
    e_z, e_x = simulate_qb_v1(ent)
    n_z, n_x = simulate_qb_v1(no_ent)
    assert all(-1.000001 <= v <= 1.000001 for v in e_z+e_x+n_z+n_x)
    assert sum((a-b)**2 for a,b in zip(e_z+e_x,n_z+n_x)) > 1e-6


@pytest.mark.parametrize("mode,source_class", [
    ("off", "none"),
    ("matched_classical", "classical"),
    ("replay", "replay"),
    ("sim_unentangled", "simulator"),
    ("sim_entangled", "simulator"),
])
def test_every_shadow_operator_has_same_validated_12d_contract(mode, source_class):
    result = operator().evaluate(
        PERSON, mode=mode, circuit_version="qb-v1", shot_budget=1024,
        provenance={"replay_key":"fixture"} if mode=="replay" else {},
    )
    assert isinstance(result, BuddyQuantumState)
    assert result.mode == mode
    assert result.source_class == source_class
    assert len(result.qstate12) == 12
    assert all(math.isfinite(v) and abs(v) <= 1 for v in result.qstate12)
    assert BuddyQuantumState.from_document(result.to_document()) == result
    assert result.job_id is None
    assert result.shot_count == 0  # deterministic statevector/replay, not live shots


def test_software_arms_deterministic_per_person_and_classical_amplitude_matched():
    op = operator()
    sim = op.evaluate(PERSON, mode="sim_entangled", circuit_version="qb-v1",
                      shot_budget=1024, provenance={})
    classical = op.evaluate(PERSON, mode="matched_classical", circuit_version="qb-v1",
                            shot_budget=1024, provenance={})
    repeat = op.evaluate(PERSON, mode="sim_entangled", circuit_version="qb-v1",
                         shot_budget=1024, provenance={})
    assert sim.qstate12 == repeat.qstate12
    sim_norm = math.sqrt(sum(v*v for v in sim.qstate12))
    classical_norm = math.sqrt(sum(v*v for v in classical.qstate12))
    assert abs(sim_norm-classical_norm) < 1e-6
    assert sim.qstate12 != classical.qstate12


def test_archived_replay_uses_existing_packet_without_fake_person_specificity():
    op = operator()
    a = op.evaluate(PERSON, mode="replay", circuit_version="qb-v1",
                    shot_budget=1024, provenance={"replay_key":"fixture"})
    b = op.evaluate([-v for v in PERSON], mode="replay", circuit_version="qb-v1",
                    shot_budget=1024, provenance={"replay_key":"fixture"})
    assert a.qstate12 == b.qstate12
    assert a.source_state_sha256 != b.source_state_sha256
    assert a.source_class == "replay"
    with pytest.raises((BuddyStateError, ValueError)):
        op.evaluate(PERSON, mode="replay", circuit_version="qb-v1",
                    shot_budget=1024, provenance={"replay_key":"missing"})


def test_invalid_state_shots_and_version_fail_before_simulation():
    op = operator()
    for vector in ([0.1]*11,[float("nan")]*12,[1.1]*12):
        with pytest.raises(BuddyStateError):
            op.evaluate(vector, mode="sim_entangled", circuit_version="qb-v1",
                        shot_budget=1024, provenance={})
    for shots in (-1, True, 100000000):
        with pytest.raises((BuddyStateError, ValueError)):
            op.evaluate(PERSON, mode="sim_entangled", circuit_version="qb-v1",
                        shot_budget=shots, provenance={})
    with pytest.raises(BuddyStateError):
        op.evaluate(PERSON, mode="sim_entangled", circuit_version="unknown",
                    shot_budget=1024, provenance={})


def test_hardware_modes_deny_without_auth_before_provider_invocation():
    calls = []
    class FakeExecutor:
        def evaluate(self, *args, **kwargs):
            calls.append((args,kwargs))
            raise AssertionError("live executor was reached")
    op = QuantumStateOperator(hardware_executor=FakeExecutor())
    for mode in ("hardware_ibm", "hardware_rigetti"):
        with pytest.raises(HardwareExecutionDisabled):
            op.evaluate(PERSON, mode=mode, circuit_version="qb-v1",
                        shot_budget=1024, provenance={})
    assert calls == []
    for policy in (
        HardwareExecutionPolicy(allow_live=True),
        HardwareExecutionPolicy(allow_live=True, cost_verified=True),
    ):
        with pytest.raises(HardwareExecutionDisabled):
            policy.require_authorized()


def test_simulated_packet_is_sensitive_to_changing_person_state():
    op = operator()
    a = op.evaluate(PERSON, mode="sim_entangled", circuit_version="qb-v1",
                    shot_budget=1024, provenance={})
    changed = list(PERSON)
    changed[1] += 0.08
    b = op.evaluate(changed, mode="sim_entangled", circuit_version="qb-v1",
                    shot_budget=1024, provenance={})
    assert a.qstate12 != b.qstate12
    assert a.circuit_sha256 != b.circuit_sha256
