import json
from pathlib import Path

import pytest

from beastbox.descendant.stage import StageInputs, create_genesis_manifest, plan_stage

PRIME = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
CANONICAL = "54328c4d2090825553e3e66773177ac3b80b5b5386027eaa899ed8dd81f32f08"


def test_training_refuses_unproven_parent() -> None:
    result = plan_stage(
        stage="CORPUS-CLEAN",
        parent_training_allowed=False,
        parent_checkpoint_sha256=None,
        inputs=StageInputs(manifest_hashes={"promotion": "a" * 64}),
        seed=1,
    )
    assert result.status == "BLOCKED_PARENT_PROVENANCE"


def test_genesis_records_canonical_reconstruction_without_claiming_optimizer_continuity() -> None:
    manifest = create_genesis_manifest(
        prime_gguf_sha256=PRIME,
        canonical_checkpoint_sha256=CANONICAL,
        reconstruction_proof_sha256="c" * 64,
        training_allowed=True,
    )
    assert manifest["parent_prime_gguf_sha256"] == PRIME
    assert manifest["trainable_parent_sha256"] == CANONICAL
    assert manifest["parent_kind"] == "canonical-trainable-reconstruction"
    assert manifest["historical_optimizer_continuity"] is False
    assert manifest["historical_raw_parameters_recovered"] is False


def test_supported_stage_plan_freezes_inputs_and_seed() -> None:
    inputs = StageInputs(manifest_hashes={"promotion": "a" * 64, "quarantine": "b" * 64})
    plan = plan_stage(
        stage="MEMORY",
        parent_training_allowed=True,
        parent_checkpoint_sha256=CANONICAL,
        inputs=inputs,
        seed=20260815,
    )
    assert plan.status == "READY"
    assert plan.stage == "MEMORY"
    assert plan.seed == 20260815
    assert plan.input_manifest_sha256
    assert plan.parent_checkpoint_sha256 == CANONICAL


def test_unknown_stage_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported stage"):
        plan_stage(
            stage="MAGIC",
            parent_training_allowed=True,
            parent_checkpoint_sha256=CANONICAL,
            inputs=StageInputs(manifest_hashes={"promotion": "a" * 64}),
            seed=1,
        )


def test_invalid_manifest_hash_is_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        StageInputs(manifest_hashes={"promotion": "nope"})
