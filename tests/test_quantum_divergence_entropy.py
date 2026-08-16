import pytest

from beastbox.quantum_divergence.entropy import classical_entropy, quantum_entropy_from_counts, tears_in_rain_wave


def test_classical_entropy_is_reproducible_and_bounded():
    a = classical_entropy(1234, 12)
    b = classical_entropy(1234, 12)
    assert a.vector == b.vector
    assert a.source == "classical-prng"
    assert len(a.vector) == 12
    assert all(-1.0 <= x <= 1.0 for x in a.vector)


def test_quantum_entropy_requires_real_ibm_provenance():
    counts = {"00": 500, "11": 524}
    with pytest.raises(ValueError, match="real IBM"):
        quantum_entropy_from_counts(
            counts,
            {
                "backend": "simulator",
                "ibm_native_job_id": "x",
                "shots_per_pub": 1024,
                "circuit_sha256": "a" * 64,
            },
            12,
        )


def test_quantum_entropy_is_bounded_and_committed():
    q = quantum_entropy_from_counts(
        {"00": 400, "01": 100, "10": 200, "11": 324},
        {
            "backend": "ibm_test_hardware",
            "ibm_native_job_id": "job-123",
            "shots_per_pub": 1024,
            "circuit_sha256": "b" * 64,
        },
        12,
    )
    assert q.source == "ibm-quantum-hardware"
    assert len(q.vector) == 12
    assert len(q.source_sha256) == 64
    assert all(-1.0 <= x <= 1.0 for x in q.vector)


def test_tears_in_rain_wave_clamps_and_rejects_nonfinite():
    assert tears_in_rain_wave([-2.0, -0.2, 0.3, 2.0]) == (-1.0, -0.2, 0.3, 1.0)
    with pytest.raises(ValueError):
        tears_in_rain_wave([float("nan")])
