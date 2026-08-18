import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from beastbox.descendant.hashing import canonical_json, sha256_bytes, sha256_file
from beastbox.descendant.lineage import (
    PRIME_GGUF_SHA256,
    DescendantCheckpointManifest,
    PrimeManifest,
    TrainableParentManifest,
)


LOCK = Path("experiments/autonomous-hands/native-stack.lock.json")


def test_canonical_json_is_order_independent_and_strict() -> None:
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert sha256_bytes(canonical_json({"a": 1})) == sha256_bytes(canonical_json({"a": 1}))
    with pytest.raises(ValueError):
        canonical_json({"bad": float("nan")})


def test_prime_manifest_is_frozen_from_exact_native_lock() -> None:
    prime = PrimeManifest.from_lock(LOCK, native_context=128)
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    assert prime.repo_id == "phera-ra/QC67_cosmo"
    assert prime.revision == "b414724c627300c41b099dcc6853766d08fd27a4"
    assert prime.gguf_path == "weights/cosmos-cst.gguf"
    assert prime.gguf_sha256 == PRIME_GGUF_SHA256
    assert prime.native_context == 128
    assert prime.source_lock_sha256 == sha256_file(LOCK)
    assert dict(prime.required_files) == lock["required_files"]

    with pytest.raises(FrozenInstanceError):
        prime.native_context = 512  # type: ignore[misc]


def test_prime_manifest_rejects_wrong_gguf_identity(tmp_path: Path) -> None:
    value = json.loads(LOCK.read_text(encoding="utf-8"))
    value["gguf_sha256"] = "0" * 64
    bad = tmp_path / "bad-lock.json"
    bad.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="Prime GGUF"):
        PrimeManifest.from_lock(bad, native_context=128)


def test_trainable_parent_does_not_imply_prime_equivalence() -> None:
    parent = TrainableParentManifest(
        artifact_path="weights/spark_cst.pt",
        artifact_sha256="a" * 64,
        provenance_status="CANDIDATE",
        prime_equivalence_proven=False,
        architecture="cosmos-spark-cst",
    )
    assert parent.training_allowed is False


def test_descendant_checkpoint_requires_distinct_parent_and_output() -> None:
    with pytest.raises(ValueError, match="parent"):
        DescendantCheckpointManifest(
            stage="D001-GENESIS",
            parent_sha256="",
            output_sha256="b" * 64,
            code_commit="c" * 40,
            corpus_manifest_sha256="d" * 64,
        )

    with pytest.raises(ValueError, match="distinct"):
        DescendantCheckpointManifest(
            stage="D001-GENESIS",
            parent_sha256="b" * 64,
            output_sha256="b" * 64,
            code_commit="c" * 40,
            corpus_manifest_sha256="d" * 64,
        )
