from beastbox.descendant.gguf import build_description, provenance_metadata


def test_unknown_quantum_source_does_not_claim_hardware_birth() -> None:
    ck = {
        "stage": "MEMORY",
        "parent_prime_gguf_sha256": "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6",
        "quantum_source": "unknown_from_prime_artifact",
    }
    description = build_description(ck).lower()
    assert "every initial weight drawn" not in description
    assert "measured ibm quantum hardware" not in description
    assert "quantum provenance unknown" in description


def test_provenance_metadata_preserves_stage_and_parent() -> None:
    ck = {
        "stage": "CORPUS-CLEAN",
        "parent_prime_gguf_sha256": "a" * 64,
        "parent_checkpoint_sha256": "b" * 64,
        "quantum_source": "unknown_from_prime_artifact",
        "historical_optimizer_continuity": False,
    }
    meta = provenance_metadata(ck)
    assert meta["d001.stage"] == "CORPUS-CLEAN"
    assert meta["d001.parent_prime_gguf_sha256"] == "a" * 64
    assert meta["d001.quantum_source"] == "unknown_from_prime_artifact"
    assert meta["d001.historical_optimizer_continuity"] is False
