from pathlib import Path
import runpy


SCRIPT = Path("scripts/descendant_parent_preflight.py")
WORKFLOW = Path(".github/workflows/d001-lineage-preflight.yml")
MODULE = None


def _module():
    global MODULE
    if MODULE is None:
        MODULE = runpy.run_path(str(SCRIPT))
    return MODULE


def test_gguf_only_is_not_trainable_parent() -> None:
    result = _module()["classify_files"](["weights/cosmos-cst.gguf"])
    assert result.status == "NO_TRAINABLE_PARENT"
    assert result.training_allowed is False
    assert result.trainable_candidates == ()


def test_trainable_file_without_equivalence_proof_is_conversion_required() -> None:
    result = _module()["classify_files"](
        ["weights/cosmos-cst.gguf", "weights/spark_cst.pt"]
    )
    assert result.status == "CONVERSION_REQUIRED"
    assert result.training_allowed is False
    assert result.trainable_candidates == ("weights/spark_cst.pt",)


def test_filename_never_proves_prime_equivalence() -> None:
    result = _module()["classify_files"](
        ["weights/cosmos-cst.gguf", "weights/cosmos-cst.safetensors"]
    )
    assert result.status != "PROVEN"
    assert result.training_allowed is False


def test_explicit_valid_proof_can_unlock_exact_candidate() -> None:
    prime_sha = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
    candidate_sha = "a" * 64
    proof = {
        "prime_gguf_sha256": prime_sha,
        "artifact_path": "weights/cosmos-cst.safetensors",
        "artifact_sha256": candidate_sha,
        "equivalence_method": "source-checkpoint-export-manifest",
    }
    result = _module()["classify_files"](
        ["weights/cosmos-cst.gguf", "weights/cosmos-cst.safetensors"],
        proof=proof,
    )
    assert result.status == "PROVEN"
    assert result.training_allowed is True
    assert result.proven_artifact == "weights/cosmos-cst.safetensors"


def test_bad_or_mismatched_proof_stays_blocked() -> None:
    proof = {
        "prime_gguf_sha256": "0" * 64,
        "artifact_path": "weights/cosmos-cst.safetensors",
        "artifact_sha256": "a" * 64,
        "equivalence_method": "source-checkpoint-export-manifest",
    }
    result = _module()["classify_files"](
        ["weights/cosmos-cst.gguf", "weights/cosmos-cst.safetensors"],
        proof=proof,
    )
    assert result.status == "CONVERSION_REQUIRED"
    assert result.training_allowed is False


def test_preflight_workflow_uses_exact_pinned_revision_and_freezes_artifact() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "phera-ra/QC67_cosmo" in workflow
    assert "b414724c627300c41b099dcc6853766d08fd27a4" in workflow
    assert "scripts/descendant_parent_preflight.py" in workflow
    assert "tests/test_descendant_parent_preflight.py" in workflow
    assert "tests/test_descendant_lineage.py" in workflow
    assert "_d001/parent-preflight.json" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "contents: read" in workflow
