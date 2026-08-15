from datetime import datetime, timezone

import pytest

from beastbox.descendant.twin import (
    build_twin_packet,
    normalize_features,
    project_dyn12,
    select_temporal_pair,
)


def test_unknown_provenance_is_not_training_eligible() -> None:
    packet = build_twin_packet(
        source_hashes=("a" * 64,),
        observed_at="2026-08-15T12:00:00+00:00",
        features={"heart_bpm": 72.0},
        provenance_class="unknown",
        reference_time="2026-08-15T12:00:05+00:00",
    )
    assert packet.training_eligible is False


def test_verified_packet_requires_hash_and_timezone_timestamp() -> None:
    with pytest.raises(ValueError, match="source hash"):
        build_twin_packet(
            source_hashes=(), observed_at="2026-08-15T12:00:00+00:00",
            features={"heart_bpm": 72.0}, provenance_class="verified_measurement",
            reference_time="2026-08-15T12:00:05+00:00",
        )
    with pytest.raises(ValueError, match="timezone"):
        build_twin_packet(
            source_hashes=("a" * 64,), observed_at="2026-08-15T12:00:00",
            features={"heart_bpm": 72.0}, provenance_class="verified_measurement",
            reference_time="2026-08-15T12:00:05+00:00",
        )


def test_missing_channels_are_explicit_not_invented() -> None:
    packet = build_twin_packet(
        source_hashes=("b" * 64,),
        observed_at="2026-08-15T12:00:00+00:00",
        features={"heart_bpm": 70.0, "mic_energy": None},
        provenance_class="verified_measurement",
        reference_time="2026-08-15T12:00:02+00:00",
    )
    assert packet.features == {"heart_bpm": 70.0}
    assert packet.missing_channels == ("mic_energy",)
    assert packet.training_eligible is True


def test_normalization_is_explicit_and_deterministic() -> None:
    values = {"heart_bpm": 80.0, "motion": 3.0}
    transforms = {
        "heart_bpm": {"offset": 60.0, "scale": 20.0},
        "motion": {"offset": 0.0, "scale": 6.0},
    }
    assert normalize_features(values, transforms) == {"heart_bpm": 1.0, "motion": 0.5}
    assert normalize_features(values, transforms) == normalize_features(values, transforms)
    with pytest.raises(ValueError, match="scale"):
        normalize_features(values, {"heart_bpm": {"offset": 0.0, "scale": 0.0}})


def test_dyn12_projection_requires_explicit_twelve_channel_order() -> None:
    features = {f"c{i}": float(i) for i in range(12)}
    order = tuple(f"c{i}" for i in range(12))
    dyn12 = project_dyn12(features, order)
    assert dyn12 == tuple(float(i) for i in range(12))
    assert project_dyn12({"c0": 1.0}, order) is None
    with pytest.raises(ValueError, match="12"):
        project_dyn12(features, order[:11])


def test_temporal_alignment_enforces_window_and_records_arm() -> None:
    packets = [
        build_twin_packet(
            source_hashes=("c" * 64,), observed_at="2026-08-15T12:00:01+00:00",
            features={"heart_bpm": 71.0}, provenance_class="verified_measurement",
            reference_time="2026-08-15T12:00:10+00:00",
        ),
        build_twin_packet(
            source_hashes=("d" * 64,), observed_at="2026-08-15T12:00:08+00:00",
            features={"heart_bpm": 73.0}, provenance_class="verified_measurement",
            reference_time="2026-08-15T12:00:10+00:00",
        ),
    ]
    pair = select_temporal_pair(
        packets,
        target_at="2026-08-15T12:00:10+00:00",
        max_offset_seconds=5.0,
        arm="aligned",
    )
    assert pair.arm == "aligned"
    assert pair.delta_seconds == -2.0
    assert pair.within_window is True

    shifted = select_temporal_pair(
        packets,
        target_at="2026-08-15T12:00:10+00:00",
        max_offset_seconds=5.0,
        arm="time_shifted",
        shift_seconds=60.0,
    )
    assert shifted.arm == "time_shifted"
    assert shifted.within_window is False


def test_packet_hash_is_stable_for_same_measured_state() -> None:
    kwargs = dict(
        source_hashes=("e" * 64,), observed_at="2026-08-15T12:00:00+00:00",
        features={"heart_bpm": 75.0, "mic_energy": 0.2}, provenance_class="verified_measurement",
        reference_time="2026-08-15T12:00:01+00:00",
    )
    assert build_twin_packet(**kwargs).packet_sha256 == build_twin_packet(**kwargs).packet_sha256
