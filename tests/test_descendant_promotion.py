import pytest

from beastbox.descendant.promotion import (
    PromotionCandidate,
    assign_split,
    audit_leakage,
    promote,
)


def candidate(**overrides):
    data = dict(
        source_hashes=("a" * 64,),
        group_id="run-007",
        text="Zeref completed the frozen run.",
        reason="validated episodic evidence",
        reviewer="d001-policy",
        policy_version="promotion-v1",
        source_disposition="CLEAN",
        source_validity="VALID",
        provenance_class="verified",
        transformations=("redact-harness-noise",),
        contamination_flags=(),
    )
    data.update(overrides)
    return PromotionCandidate(**data)


def test_rejects_quarantine_invalid_and_unproven_measurements() -> None:
    with pytest.raises(ValueError, match="quarantined"):
        promote(candidate(source_disposition="QUARANTINE"), split_seed="d001")
    with pytest.raises(ValueError, match="invalid source"):
        promote(candidate(source_validity="INVALID_DURATION"), split_seed="d001")
    with pytest.raises(ValueError, match="provenance"):
        promote(candidate(provenance_class="unknown"), split_seed="d001")


def test_promotion_record_is_deterministic() -> None:
    a = promote(candidate(), split_seed="d001")
    b = promote(candidate(), split_seed="d001")
    assert a.example_sha256 == b.example_sha256
    assert a.partition == b.partition
    assert a.source_hashes == ("a" * 64,)


def test_group_assignment_is_stable_and_group_safe() -> None:
    first = assign_split("session-1", seed="d001")
    assert first == assign_split("session-1", seed="d001")
    assert first in {"train", "validation", "holdout"}


def test_leakage_audit_rejects_source_hash_cross_partition() -> None:
    a = promote(candidate(group_id="g1"), split_seed="d001")
    b = promote(candidate(group_id="g2", source_hashes=a.source_hashes), split_seed="other-seed")
    if a.partition == b.partition:
        b = b.__class__(**{**b.__dict__, "partition": "holdout" if a.partition != "holdout" else "train"})
    report = audit_leakage([a, b])
    assert report["valid"] is False
    assert report["source_hash_leaks"]


def test_leakage_audit_rejects_group_cross_partition() -> None:
    a = promote(candidate(group_id="same"), split_seed="d001")
    other_partition = "holdout" if a.partition != "holdout" else "train"
    b = a.__class__(**{**a.__dict__, "source_hashes": ("b" * 64,), "example_sha256": "c" * 64, "partition": other_partition})
    report = audit_leakage([a, b])
    assert report["valid"] is False
    assert report["group_leaks"] == ["same"]


def test_duplicate_source_hash_within_same_partition_is_rejected() -> None:
    a = promote(candidate(group_id="same"), split_seed="d001")
    b = a.__class__(**{**a.__dict__, "example_sha256": "d" * 64})
    report = audit_leakage([a, b])
    assert report["valid"] is False
    assert report["duplicate_source_hashes"]
