from __future__ import annotations

import math

import pytest

from beastbox.cns7_ibm_ignition_v2 import (
    ARM_MINUS,
    ARM_PLUS,
    ARM_ZERO,
    BODY_DIMS,
    BODY_PUBS_PER_BACKEND,
    CNS7_ORGAN_QUBITS,
    COUPLING_COEFFICIENT,
    DYN12_QUBITS,
    DYN42_QUBITS,
    EPOCHS,
    JOBS_PER_BACKEND,
    PLANNED_PRIMARY_PUBS,
    PLANNED_PRIMARY_SHOTS,
    PUBS_PER_JOB,
    SHOTS_PER_PUB,
    arms,
    build_body_template,
    build_job_schedule,
    coupling_angle,
    coupling_edges,
    ideal_local_observables,
    retry_decision,
    template_binding,
)


def test_exact_12d_42d_54d_and_seven_organ_mapping() -> None:
    assert BODY_DIMS == 54
    assert DYN12_QUBITS == tuple(range(12))
    assert DYN42_QUBITS == tuple(range(12, 54))
    assert list(CNS7_ORGAN_QUBITS) == [
        "quantum",
        "dark_matter",
        "emeth",
        "plasticity",
        "awareness",
        "daemons",
        "surgeon",
    ]
    assert tuple(CNS7_ORGAN_QUBITS["quantum"]) == tuple(range(12, 18))
    assert tuple(CNS7_ORGAN_QUBITS["surgeon"]) == tuple(range(48, 54))
    flat = tuple(q for role in CNS7_ORGAN_QUBITS for q in CNS7_ORGAN_QUBITS[role])
    assert flat == DYN42_QUBITS


def test_coupling_topology_is_two_rings_with_exactly_54_edges() -> None:
    edges = coupling_edges()
    assert len(edges) == 54
    assert len(set(edges)) == 54

    dyn12_edges = edges[:12]
    dyn42_edges = edges[12:]
    assert dyn12_edges == tuple((i, (i + 1) % 12) for i in range(12))
    assert dyn42_edges == tuple((12 + i, 12 + ((i + 1) % 42)) for i in range(42))


def test_coupling_angle_uses_existing_006_software_coefficient() -> None:
    assert COUPLING_COEFFICIENT == pytest.approx(0.06)
    assert coupling_angle(0.5, -0.5) == pytest.approx(math.pi * 0.06)
    assert coupling_angle(-0.5, 0.5) == pytest.approx(-math.pi * 0.06)
    assert coupling_angle(0.2, 0.2) == pytest.approx(0.0)


def test_signed_local_observables_have_frozen_even_odd_symmetry() -> None:
    state = [0.7 * math.sin((i + 1) * 0.17) for i in range(54)]
    plus = ideal_local_observables(state, arm=ARM_PLUS)
    zero = ideal_local_observables(state, arm=ARM_ZERO)
    minus = ideal_local_observables(state, arm=ARM_MINUS)

    assert len(plus["X"]) == len(plus["Y"]) == len(plus["Z"]) == 54
    for i in range(54):
        assert plus["Z"][i] == pytest.approx(state[i], abs=1e-12)
        assert zero["Z"][i] == pytest.approx(state[i], abs=1e-12)
        assert minus["Z"][i] == pytest.approx(state[i], abs=1e-12)
        assert plus["X"][i] == pytest.approx(minus["X"][i], abs=1e-12)
        assert plus["Y"][i] == pytest.approx(-minus["Y"][i], abs=1e-12)
        assert zero["Y"][i] == pytest.approx(0.0, abs=1e-12)


def test_same_symbolic_template_is_bound_for_all_three_arms() -> None:
    state = [0.5 * math.cos((i + 1) * 0.11) for i in range(54)]
    template = build_body_template("Y")
    op_signature = template.count_ops()

    bound = []
    for arm in arms():
        values = template_binding(state, arm=arm)
        circuit = template.assign_parameters(values, inplace=False)
        assert circuit.num_qubits == 54
        assert circuit.num_clbits == 54
        assert circuit.count_ops() == op_signature
        assert len(circuit.parameters) == 0
        bound.append(circuit)

    assert [c.count_ops() for c in bound] == [op_signature, op_signature, op_signature]
    assert op_signature.get("rzz", 0) == 54
    assert op_signature.get("ry", 0) == 54


def test_job_schedule_is_two_epochs_per_job_plus_cal0_cal1_and_seed() -> None:
    schedule = build_job_schedule()
    assert EPOCHS == 12
    assert JOBS_PER_BACKEND == 6
    assert len(schedule) == 6
    assert [job["epochs"] for job in schedule] == [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12]]
    for job in schedule:
        assert len(job["body_pubs"]) == 18
        assert job["calibration_pubs"] == ["CAL0", "CAL1"]
        assert job["origin_seed_pubs"] == 1
        assert job["total_pubs"] == PUBS_PER_JOB == 21

    assert BODY_PUBS_PER_BACKEND == 108
    assert PLANNED_PRIMARY_PUBS == 252
    assert SHOTS_PER_PUB == 4096
    assert PLANNED_PRIMARY_SHOTS == 1_032_192


def test_retry_rule_is_status_only_zero_execution_and_bounded_once() -> None:
    zero_execution = {"circuits_execution_time_ns": 0, "qpu_charge_time_seconds": 0}
    nonzero_execution = {"circuits_execution_time_ns": 1, "qpu_charge_time_seconds": 0.1}

    assert retry_decision(status="DONE", metrics=zero_execution, retries_used=0) == "NO_RETRY"
    assert retry_decision(status="ERROR", metrics=zero_execution, retries_used=0) == "RETRY_EXACT_QPY_ONCE"
    assert retry_decision(status="ERROR", metrics=zero_execution, retries_used=1) == "INCONCLUSIVE"
    assert retry_decision(status="ERROR", metrics=nonzero_execution, retries_used=0) == "INCONCLUSIVE"
    assert retry_decision(status="RUNNING", metrics=zero_execution, retries_used=0) == "WAIT"
