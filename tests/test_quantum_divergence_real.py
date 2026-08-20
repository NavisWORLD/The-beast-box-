import pytest

pytest.importorskip("qiskit")

from beastbox.quantum_divergence.real import build_hardware_entropy_circuit


def test_hardware_entropy_circuit_is_measurement_only_after_superposition():
    qc = build_hardware_entropy_circuit(12)
    assert qc.num_qubits == 12
    assert qc.num_clbits == 12
    names = [instruction.operation.name for instruction in qc.data]
    assert names.count("h") == 12
    assert names.count("measure") == 12


def test_hardware_entropy_circuit_rejects_nonpositive_width():
    try:
        build_hardware_entropy_circuit(0)
    except ValueError as exc:
        assert "positive" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
