from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from beastbox.training.lineage import build_parent_manifest, sha256_file, verify_parent_manifest, write_canonical_json

REPO_ROOT = Path(__file__).resolve().parents[1]


def _fixture_files(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    checkpoint = tmp_path / "zeref.pt"
    architecture = tmp_path / "arch.py"
    tokenizer = tmp_path / "tokenizer.json"
    ledger = tmp_path / "ledger.jsonl"
    checkpoint.write_bytes(b"checkpoint-v1")
    architecture.write_text("ARCH = 1\n", encoding="utf-8")
    tokenizer.write_text('{"a":0}\n', encoding="utf-8")
    ledger.write_text('{"memory_id":1}\n', encoding="utf-8")
    return checkpoint, architecture, tokenizer, ledger


def test_parent_manifest_hashes_exact_files_and_verifies(tmp_path: Path):
    checkpoint, architecture, tokenizer, ledger = _fixture_files(tmp_path)
    manifest = build_parent_manifest(
        model_id="zeref-genesis-baseline",
        checkpoint_path=checkpoint.name,
        architecture_path=architecture.name,
        tokenizer_path=tokenizer.name,
        memory_ledger_path=ledger.name,
        root=tmp_path,
    )

    assert manifest["schema"] == "zeref-phos-parent-manifest-v1"
    assert manifest["model_id"] == "zeref-genesis-baseline"
    assert manifest["artifacts"]["checkpoint"]["sha256"]
    result = verify_parent_manifest(manifest, root=tmp_path)
    assert result == {
        "verified": True,
        "model_id": "zeref-genesis-baseline",
        "artifact_count": 4,
    }


def test_parent_manifest_fails_on_expected_checkpoint_mismatch(tmp_path: Path):
    checkpoint, architecture, _, _ = _fixture_files(tmp_path)
    with pytest.raises(RuntimeError, match="checkpoint SHA-256 mismatch"):
        build_parent_manifest(
            model_id="zeref-genesis-baseline",
            checkpoint_path=checkpoint.name,
            architecture_path=architecture.name,
            tokenizer_path=None,
            memory_ledger_path=None,
            root=tmp_path,
            expected_checkpoint_sha256="0" * 64,
        )


def test_parent_manifest_fails_on_expected_architecture_mismatch(tmp_path: Path):
    checkpoint, architecture, _, _ = _fixture_files(tmp_path)
    with pytest.raises(RuntimeError, match="architecture SHA-256 mismatch"):
        build_parent_manifest(
            model_id="zeref-genesis-baseline",
            checkpoint_path=checkpoint.name,
            architecture_path=architecture.name,
            tokenizer_path=None,
            memory_ledger_path=None,
            root=tmp_path,
            expected_architecture_sha256="f" * 64,
        )


def test_verification_fails_after_artifact_mutation(tmp_path: Path):
    checkpoint, architecture, tokenizer, ledger = _fixture_files(tmp_path)
    manifest = build_parent_manifest(
        model_id="zeref-genesis-baseline",
        checkpoint_path=checkpoint.name,
        architecture_path=architecture.name,
        tokenizer_path=tokenizer.name,
        memory_ledger_path=ledger.name,
        root=tmp_path,
    )
    checkpoint.write_bytes(b"checkpoint-mutated")
    with pytest.raises(RuntimeError, match="checkpoint SHA-256 mismatch"):
        verify_parent_manifest(manifest, root=tmp_path)


def test_manifest_rejects_path_traversal(tmp_path: Path):
    checkpoint, architecture, _, _ = _fixture_files(tmp_path)
    manifest = build_parent_manifest(
        model_id="zeref-genesis-baseline",
        checkpoint_path=checkpoint.name,
        architecture_path=architecture.name,
        tokenizer_path=None,
        memory_ledger_path=None,
        root=tmp_path,
    )
    manifest["artifacts"]["checkpoint"]["path"] = "../outside.pt"
    with pytest.raises(ValueError, match="outside root"):
        verify_parent_manifest(manifest, root=tmp_path)


def test_parent_manifest_rejects_empty_model_id(tmp_path: Path):
    checkpoint, architecture, _, _ = _fixture_files(tmp_path)
    with pytest.raises(ValueError, match="model_id"):
        build_parent_manifest(
            model_id="   ",
            checkpoint_path=checkpoint.name,
            architecture_path=architecture.name,
            tokenizer_path=None,
            memory_ledger_path=None,
            root=tmp_path,
        )


def test_manifest_rejects_secret_like_keys(tmp_path: Path):
    checkpoint, architecture, _, _ = _fixture_files(tmp_path)
    manifest = build_parent_manifest(
        model_id="zeref-genesis-baseline",
        checkpoint_path=checkpoint.name,
        architecture_path=architecture.name,
        tokenizer_path=None,
        memory_ledger_path=None,
        root=tmp_path,
    )
    manifest["api_key"] = "do-not-store"
    with pytest.raises(ValueError, match="secret-like"):
        verify_parent_manifest(manifest, root=tmp_path)


def test_write_canonical_json_returns_file_hash_and_stable_bytes(tmp_path: Path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    left = {"z": 1, "a": {"b": 2}}
    right = {"a": {"b": 2}, "z": 1}

    first_sha = write_canonical_json(first, left)
    second_sha = write_canonical_json(second, right)

    assert first.read_bytes() == second.read_bytes()
    assert first_sha == second_sha
    assert first.read_text(encoding="utf-8").endswith("\n")


def test_freeze_zeref_genesis_cli_writes_and_verifies_manifest(tmp_path: Path):
    checkpoint, architecture, tokenizer, ledger = _fixture_files(tmp_path)
    output = tmp_path / "genesis.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/freeze_zeref_genesis.py",
            "--root",
            str(tmp_path),
            "--checkpoint",
            checkpoint.name,
            "--architecture",
            architecture.name,
            "--tokenizer",
            tokenizer.name,
            "--memory-ledger",
            ledger.name,
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert summary["verified"] is True
    assert summary["model_id"] == "zeref-genesis-baseline"
    assert summary["manifest_sha256"] == sha256_file(output)
    assert verify_parent_manifest(manifest, root=tmp_path)["verified"] is True


def test_freeze_zeref_genesis_cli_fails_on_expected_hash_mismatch(tmp_path: Path):
    checkpoint, architecture, _, _ = _fixture_files(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/freeze_zeref_genesis.py",
            "--root",
            str(tmp_path),
            "--checkpoint",
            checkpoint.name,
            "--architecture",
            architecture.name,
            "--expected-checkpoint-sha256",
            "0" * 64,
            "--out",
            str(tmp_path / "genesis.json"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "checkpoint SHA-256 mismatch" in result.stderr
