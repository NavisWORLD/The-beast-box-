import math

from scripts.collect_zeref_quantum_lifesource_ibm import (
    build_bell_source_circuit,
    build_chsh_circuits,
    build_nonentangled_control_circuit,
    deterministic_backend_order,
    experiment_tags,
)


class _Status:
    def __init__(self, operational, pending_jobs):
        self.operational = operational
        self.pending_jobs = pending_jobs


class _Backend:
    def __init__(self, name, operational=True, pending_jobs=0, num_qubits=127):
        self.name = name
        self.num_qubits = num_qubits
        self._status = _Status(operational, pending_jobs)

    def status(self):
        return self._status


def test_bell_and_nonentangled_controls_match_logical_shape_and_depth():
    bell = build_bell_source_circuit()
    control = build_nonentangled_control_circuit()
    assert bell.num_qubits == control.num_qubits == 2
    assert bell.num_clbits == control.num_clbits == 2
    assert bell.depth() == control.depth() == 3  # two preparation layers plus measurement
    assert bell.count_ops().get("cx", 0) == 1
    assert control.count_ops().get("cx", 0) == 0
    assert not any(getattr(op.operation, "num_qubits", 0) > 1 and op.operation.name != "barrier" for op in control.data)


def test_chsh_circuit_set_is_frozen_and_measured():
    rows = build_chsh_circuits()
    assert set(rows) == {"a0b0", "a0b1", "a1b0", "a1b1"}
    for circuit in rows.values():
        assert circuit.num_qubits == 2
        assert circuit.num_clbits == 2
        assert circuit.count_ops().get("cx", 0) == 1
        assert circuit.count_ops().get("measure", 0) == 2
    assert math.isclose(rows["a0b0"].metadata["b_angle"], math.pi / 4)
    assert math.isclose(rows["a0b1"].metadata["b_angle"], -math.pi / 4)


def test_backend_order_is_deterministic_and_rejects_ineligible_backends():
    backends = [
        _Backend("zeta", pending_jobs=2),
        _Backend("beta", pending_jobs=1),
        _Backend("alpha", pending_jobs=1),
        _Backend("offline", operational=False, pending_jobs=0),
        _Backend("tiny", pending_jobs=0, num_qubits=1),
    ]
    assert [backend.name for backend in deterministic_backend_order(backends)] == ["alpha", "beta", "zeta"]


def test_job_tags_are_stable_and_contain_no_credentials():
    tags = experiment_tags(prereg_sha256="a" * 64, phase="discovery", source="A")
    assert tags == ["zeref-lifesource-v1", "prereg-aaaaaaaaaaaa", "phase-discovery", "source-A"]
    lowered = " ".join(tags).lower()
    assert "token" not in lowered
    assert "secret" not in lowered
