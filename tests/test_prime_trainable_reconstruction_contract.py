from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "d001-prime-trainable-reconstruction.yml"
PRIME_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
PINNED_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"


def test_prime_trainable_reconstruction_workflow_is_hard_gated():
    assert WORKFLOW.exists(), "reconstruction workflow must exist before the parent gate can be lifted"
    text = WORKFLOW.read_text(encoding="utf-8")

    # Exact immutable source identity.
    assert PRIME_SHA in text
    assert PINNED_REVISION in text
    assert "weights/cosmos-cst.gguf" in text
    assert "architecture/cst_to_gguf.py" in text

    # Canonical inverse must not claim recovery of hidden historical parameters.
    assert "canonical_reconstruction" in text
    assert "historical_raw_parameters_recovered" in text
    assert "False" in text

    # The reconstruction is permitted only after an exact round trip.
    assert "all_61_tensors_bitwise_equal" in text
    assert "tokenizer_equal" in text
    assert "roundtrip_gguf_sha256" in text
    assert "training_allowed" in text
    assert "assert report['all_61_tensors_bitwise_equal']" in text
    assert "assert report['tokenizer_equal']" in text
    assert "assert report['roundtrip_gguf_sha256'] == PRIME_SHA" in text

    # Provenance cannot be borrowed from the later Spark sibling.
    assert "quantum_source" in text
    assert "unknown_from_prime_artifact" in text
    assert "ibm_real_shots" not in text

    # Read-only source access and artifact-only result; no Hub write/push.
    lowered = text.lower()
    assert "contents: read" in lowered
    assert "upload-artifact" in lowered
    assert "hf_api.create" not in lowered
    assert "upload_file" not in lowered
    assert "git push" not in lowered
