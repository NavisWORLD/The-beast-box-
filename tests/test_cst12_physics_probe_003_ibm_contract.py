from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class FakeStatus:
    operational: bool = True
    pending_jobs: int = 0


class FakeBackend:
    def __init__(self, name: str, *, qubits: int = 127, pending: int = 0, simulator: bool = False, twoq: float = 0.01):
        self.name = name
        self.num_qubits = qubits
        self._status = FakeStatus(True, pending)
        self.simulator = simulator
        self.median_two_qubit_error = twoq

    def status(self):
        return self._status


def test_backend_selection_requires_two_distinct_real_devices():
    from scripts.run_cst12_physics_probe_003_ibm import select_stage_backends

    a = FakeBackend("ibm_a", pending=1, twoq=0.02)
    b = FakeBackend("ibm_b", pending=2, twoq=0.01)
    out = select_stage_backends([a, b])
    assert out["discovery"].name == "ibm_a"
    assert out["replication"].name == "ibm_b"
    assert out["independent_backend_replication"] is True

    with pytest.raises(RuntimeError):
        select_stage_backends([a])
    with pytest.raises(RuntimeError):
        select_stage_backends([FakeBackend("sim", simulator=True), a])
    with pytest.raises(RuntimeError):
        select_stage_backends([FakeBackend("tiny", qubits=5), a])


def test_schedule_is_exactly_32_blocks_and_8_jobs_per_stage():
    from scripts.run_cst12_physics_probe_003_ibm import balanced_block_plan, chunk_block_plan

    layouts = [tuple(range(i, i + 7)) for i in (0, 10, 20, 30)]
    plan = balanced_block_plan("discovery", layouts, arm_order_seed=12345)
    assert len(plan) == 32
    assert {tuple(row["layout"]) for row in plan} == set(layouts)
    assert all(len(row["pub_order"]) == 16 for row in plan)
    chunks = chunk_block_plan(plan, blocks_per_job=4)
    assert len(chunks) == 8
    assert all(len(c) == 4 for c in chunks)


def test_count_sanitization_is_one_bit_and_exact_shots():
    from scripts.run_cst12_physics_probe_003_ibm import sanitize_counts, expectation_from_counts

    counts = sanitize_counts({"0": 3000, "1": 1096}, shots=4096)
    assert counts == {"0": 3000, "1": 1096}
    assert expectation_from_counts(counts, shots=4096) == pytest.approx((3000 - 1096) / 4096)
    with pytest.raises(ValueError):
        sanitize_counts({"00": 4096}, shots=4096)
    with pytest.raises(ValueError):
        sanitize_counts({"0": 4095}, shots=4096)


def _stage(*, passed: bool, effect: float, complete: bool = True, mirror: bool = True, backend: str = "ibm_a"):
    return {
        "passed": passed,
        "effect": effect,
        "complete": complete,
        "integrity_passed": complete,
        "mirror_gate": mirror,
        "backend": backend,
    }


def test_final_decision_table_is_fail_closed():
    from scripts.analyze_cst12_physics_probe_003 import classify_final_verdict

    discovery = _stage(passed=False, effect=0.001, backend="ibm_a")
    replication = _stage(passed=False, effect=0.002, backend="ibm_b")
    assert classify_final_verdict(discovery, replication) == "NULL_COMPATIBLE"

    bad = _stage(passed=False, effect=0.0, complete=False, backend="ibm_b")
    assert classify_final_verdict(discovery, bad) == "INCONCLUSIVE"

    mirror_bad = _stage(passed=False, effect=0.0, mirror=False, backend="ibm_b")
    assert classify_final_verdict(discovery, mirror_bad) == "INCONCLUSIVE"

    d = _stage(passed=True, effect=0.02, backend="ibm_a")
    r = _stage(passed=True, effect=0.018, backend="ibm_b")
    assert classify_final_verdict(d, r) == "ANOMALY_CANDIDATE"

    opposite = _stage(passed=True, effect=-0.018, backend="ibm_b")
    assert classify_final_verdict(d, opposite) == "NULL_COMPATIBLE"

    same_backend = _stage(passed=True, effect=0.018, backend="ibm_a")
    assert classify_final_verdict(d, same_backend) == "INCONCLUSIVE"
