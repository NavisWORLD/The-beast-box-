import math

import pytest

from beastbox.descendant.quantum import (
    QuantumEvidenceRecord,
    classify_source,
    derive_feature_packet,
)


def test_ibm_hardware_requires_explicit_backend_and_job_proof() -> None:
    assert classify_source(provider="IBM", backend="ibm_kyiv", job_id="abc123", simulator=False) == "hardware"
    assert classify_source(provider="IBM", backend=None, job_id="abc123", simulator=False) == "unknown"
    assert classify_source(provider="IBM", backend="ibm_kyiv", job_id=None, simulator=False) == "unknown"


def test_explicit_simulator_and_controls_never_classify_as_hardware() -> None:
    assert classify_source(provider="IBM", backend="aer_simulator", job_id="job", simulator=True) == "simulator"
    assert classify_source(provider="local", backend="python-prng", job_id=None, simulator=False, control_kind="prng") == "prng"
    assert classify_source(provider="local", backend="seeded", job_id=None, simulator=False, control_kind="fixed_seed") == "fixed_seed"


def test_evidence_requires_source_hash_and_positive_shots() -> None:
    with pytest.raises(ValueError, match="source_sha256"):
        QuantumEvidenceRecord(
            provider="IBM", backend="ibm_kyiv", source_class="hardware", shot_count=10,
            source_sha256="", job_id="j", circuit_id="c", confidence="verified", reason="job manifest"
        )
    with pytest.raises(ValueError, match="shot_count"):
        QuantumEvidenceRecord(
            provider="IBM", backend="ibm_kyiv", source_class="hardware", shot_count=0,
            source_sha256="a" * 64, job_id="j", circuit_id="c", confidence="verified", reason="job manifest"
        )


def test_hardware_record_rejects_missing_job_or_backend() -> None:
    with pytest.raises(ValueError, match="hardware provenance"):
        QuantumEvidenceRecord(
            provider="IBM", backend=None, source_class="hardware", shot_count=10,
            source_sha256="a" * 64, job_id="j", circuit_id="c", confidence="verified", reason="claimed"
        )


def test_feature_derivation_is_deterministic_and_normalized() -> None:
    evidence = QuantumEvidenceRecord(
        provider="IBM",
        backend="ibm_kyiv",
        source_class="hardware",
        shot_count=8,
        source_sha256="a" * 64,
        job_id="job-1",
        circuit_id="bell-1",
        confidence="verified",
        reason="provider job manifest",
    )
    counts = {"00": 4, "11": 4}
    a = derive_feature_packet(evidence, counts)
    b = derive_feature_packet(evidence, {"11": 4, "00": 4})
    assert a.packet_sha256 == b.packet_sha256
    assert a.source_class == "hardware"
    assert math.isclose(a.features["shannon_entropy_bits"], 1.0, rel_tol=1e-9)
    assert math.isclose(a.features["normalized_entropy"], 0.5, rel_tol=1e-9)
    assert math.isclose(a.features["bit_one_fraction"], 0.5, rel_tol=1e-9)
    assert math.isclose(a.features["adjacent_bit_agreement"], 1.0, rel_tol=1e-9)


def test_count_total_must_match_shot_count() -> None:
    evidence = QuantumEvidenceRecord(
        provider="unknown", backend=None, source_class="unknown", shot_count=8,
        source_sha256="b" * 64, job_id=None, circuit_id=None, confidence="unknown", reason="no manifest"
    )
    with pytest.raises(ValueError, match="shot count"):
        derive_feature_packet(evidence, {"0": 3, "1": 4})


def test_invalid_bitstrings_are_rejected() -> None:
    evidence = QuantumEvidenceRecord(
        provider="local", backend="seeded", source_class="fixed_seed", shot_count=2,
        source_sha256="c" * 64, job_id=None, circuit_id="control", confidence="deterministic", reason="fixed seed"
    )
    with pytest.raises(ValueError, match="bitstring"):
        derive_feature_packet(evidence, {"0x": 1, "11": 1})
