import pytest

from beastbox.descendant.evaluation import (
    EvaluationRecord,
    MechanismLiveness,
    compare_loss,
    score_sensor_claims,
)

SHA = "a" * 64


def test_evaluation_record_requires_hashes_metric_and_sensor_declaration() -> None:
    record = EvaluationRecord(
        stage="PRIME",
        model_sha256=SHA,
        dataset_sha256="b" * 64,
        test_sha256="c" * 64,
        metric_name="heldout_char_cross_entropy",
        metric_definition="mean next-character cross entropy over deterministic holdout windows",
        value=3.0,
        status="COMPLETED",
        sensor_availability={"camera": False, "microphone": False},
    )
    assert record.status == "COMPLETED"
    with pytest.raises(ValueError, match="SHA-256"):
        EvaluationRecord(
            stage="BAD", model_sha256="bad", dataset_sha256="b" * 64, test_sha256="c" * 64,
            metric_name="loss", metric_definition="defined", value=1.0, status="COMPLETED",
            sensor_availability={"camera": False},
        )


def test_sensor_claim_scoring_only_flags_claims_when_sensor_absent() -> None:
    text = "I can see the room light and hear 599 Hz through my camera."
    report = score_sensor_claims(text, {"camera": False, "microphone": False})
    assert report["flagged"] is True
    assert "camera" in report["terms"]
    assert "hear" in report["terms"]
    allowed = score_sensor_claims(text, {"camera": True, "microphone": True})
    assert allowed["flagged"] is False


def test_image_language_is_flagged_without_camera() -> None:
    report = score_sensor_claims("The image shows a dark room.", {"camera": False, "microphone": False})
    assert report["flagged"] is True
    assert "image" in report["terms"]


def test_mechanism_liveness_rejects_degenerate_state_or_missing_gradients() -> None:
    healthy = MechanismLiveness(
        layer=0, state_variance=0.02, affinity_std=0.1, affinity_identity_distance=0.4,
        gate_value=0.02, gate_grad_abs=1e-4, w54_grad_norm=2e-3, sigma=1.0,
        causal=True,
    )
    assert healthy.live is True
    dead = MechanismLiveness(
        layer=0, state_variance=0.0, affinity_std=0.0, affinity_identity_distance=0.0,
        gate_value=0.02, gate_grad_abs=0.0, w54_grad_norm=0.0, sigma=1.0,
        causal=True,
    )
    assert dead.live is False


def test_loss_comparison_is_bounded_and_neutral() -> None:
    better = compare_loss(3.0, 2.5)
    assert better["delta"] == pytest.approx(-0.5)
    assert better["direction"] == "lower"
    worse = compare_loss(2.0, 2.2)
    assert worse["direction"] == "higher"
    equal = compare_loss(2.0, 2.0)
    assert equal["direction"] == "equal"
